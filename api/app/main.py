"""Ladewüste API: serves the gold tables, the quality report and the greedy planner.

Run: make api  (uvicorn api.app.main:app on :8000). Docs at /docs.
"""

import json
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse

from api.app.db import DataNotReady, GoldStore, gold_dir_from_env
from api.app.models import (
    AppConfig,
    ErrorResponse,
    Hex,
    HexesResponse,
    Operator,
    PlanResponse,
    PlanSite,
    QualityReport,
    Station,
    StationsResponse,
)
from pipeline.config import MANIFEST_PATH, load_config
from pipeline.geo import plan_sites

NOT_READY = {503: {"model": ErrorResponse, "description": "Gold data missing: run `make pipeline`."}}
MAX_STATIONS = 5000


def create_app(gold_dir: Path | None = None) -> FastAPI:
    """App factory. Tests pass a small synthetic gold_dir; production uses data/gold."""
    app = FastAPI(
        title="Ladewüste API",
        version="0.4.0",
        description="Germany's HPC charging deserts, from the Bundesnetzagentur Ladesäulenregister "
        "(CC BY 4.0, Bundesnetzagentur.de).",
    )
    app.state.gold_dir = gold_dir or gold_dir_from_env()
    app.state.store = None
    app.state.plan_cache = {}
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    register_routes(app)
    return app


def get_store(request: Request) -> GoldStore:
    """Open the gold store on first use, so the API starts even before the pipeline has run."""
    if request.app.state.store is None:
        try:
            request.app.state.store = GoldStore(request.app.state.gold_dir)
        except DataNotReady as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    return request.app.state.store


Store = Annotated[GoldStore, Depends(get_store)]


def coverage_config() -> dict[str, Any]:
    return load_config()["coverage"]


def parse_bbox(bbox: str) -> list[float]:
    """'min_lon,min_lat,max_lon,max_lat' -> four floats, or 422."""
    try:
        values = [float(v) for v in bbox.split(",")]
    except ValueError:
        values = []
    if len(values) != 4:
        raise HTTPException(status_code=422, detail="bbox must be 'min_lon,min_lat,max_lon,max_lat'")
    min_lon, min_lat, max_lon, max_lat = values
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise HTTPException(status_code=422, detail="bbox must have min < max and valid lon/lat ranges")
    return values


BBOX_DESCRIPTION = "min_lon,min_lat,max_lon,max_lat (WGS84), e.g. 13.0,52.3,13.8,52.7"


def register_routes(app: FastAPI) -> None:
    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """The API has no page of its own: send browsers to the interactive docs."""
        return RedirectResponse(url="/docs")

    @app.get("/config", response_model=AppConfig, tags=["meta"])
    def get_config() -> AppConfig:
        config = load_config()
        coverage, source = config["coverage"], config["source"]
        data_file = None
        if MANIFEST_PATH.exists():
            data_file = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("file")
        return AppConfig(
            hpc_threshold_kw=coverage["hpc_threshold_kw"],
            desert_radius_km=coverage["desert_radius_km"],
            hub_min_hpc_points=coverage["hub_min_hpc_points"],
            h3_res_map=coverage["h3_resolutions"]["map"],
            h3_res_detail=coverage["h3_resolutions"]["detail"],
            attribution=source["attribution"],
            licence=source["licence"],
            licence_url=source["licence_url"],
            data_file=data_file,
        )

    @app.get("/hexes", response_model=HexesResponse, responses=NOT_READY, tags=["map"])
    def get_hexes(
        store: Store,
        res: Annotated[int, Query(description="H3 resolution: the map or the detail resolution from /config.")],
        min_kw: Annotated[float | None, Query(ge=0, description="Count only points with at least this power.")] = None,
        operator: Annotated[str | None, Query(description="Count only this operator's points.")] = None,
        bbox: Annotated[str | None, Query(description=BBOX_DESCRIPTION + ". Required for the detail resolution.")] = None,
    ) -> HexesResponse:
        resolutions = coverage_config()["h3_resolutions"]
        if res not in (resolutions["map"], resolutions["detail"]):
            raise HTTPException(status_code=422, detail=f"res must be {resolutions['map']} or {resolutions['detail']}")
        if res == resolutions["detail"] and bbox is None:
            raise HTTPException(status_code=422, detail=f"bbox is required for res={res} (too many cells otherwise)")
        cell_column = "cell_map" if res == resolutions["map"] else "cell_detail"
        box = parse_bbox(bbox) if bbox else [-180.0, -90.0, 180.0, 90.0]

        # Filters re-aggregate the counts from points. Distances and the desert flag come
        # straight from the hexes table: coverage is about hubs, not about the display filter.
        rows = store.rows(
            f"""
            WITH filtered AS (
                SELECT * FROM points
                WHERE ($min_kw IS NULL OR power_kw >= $min_kw)
                  AND ($operator IS NULL OR operator = $operator)
            ),
            totals AS (
                SELECT {cell_column} AS cell,
                       count(DISTINCT station_id) AS n_stations,
                       count(*) AS n_points,
                       sum(power_kw) AS total_kw,
                       count(*) FILTER (WHERE is_hpc) AS n_hpc_points,
                       coalesce(sum(power_kw) FILTER (WHERE is_hpc), 0) AS hpc_kw
                FROM filtered GROUP BY 1
            ),
            top_operators AS (
                SELECT cell, list(operator ORDER BY n DESC, operator)[1:3] AS top_operators
                FROM (SELECT {cell_column} AS cell, operator, count(*) AS n FROM filtered GROUP BY ALL)
                GROUP BY cell
            )
            SELECT h.cell, h.lat, h.lon, h.area_km2,
                   coalesce(t.n_stations, 0) AS n_stations,
                   coalesce(t.n_points, 0) AS n_points,
                   coalesce(t.total_kw, 0) AS total_kw,
                   coalesce(t.n_hpc_points, 0) AS n_hpc_points,
                   coalesce(t.hpc_kw, 0) AS hpc_kw,
                   coalesce(o.top_operators, []::VARCHAR[]) AS top_operators,
                   h.nearest_hpc_km, h.nearest_hub_km, h.is_desert
            FROM hexes AS h
            LEFT JOIN totals AS t USING (cell)
            LEFT JOIN top_operators AS o USING (cell)
            WHERE h.res = $res
              AND h.lon BETWEEN $min_lon AND $max_lon
              AND h.lat BETWEEN $min_lat AND $max_lat
            ORDER BY h.cell
            """,
            {"min_kw": min_kw, "operator": operator, "res": res,
             "min_lon": box[0], "min_lat": box[1], "max_lon": box[2], "max_lat": box[3]},
        )
        hexes = [Hex(**row) for row in rows]
        return HexesResponse(
            res=res,
            min_kw=min_kw,
            operator=operator,
            desert_km2=sum(h.area_km2 for h in hexes if h.is_desert),
            total_km2=sum(h.area_km2 for h in hexes),
            hexes=hexes,
        )

    @app.get("/stations", response_model=StationsResponse, responses=NOT_READY, tags=["map"])
    def get_stations(
        store: Store,
        bbox: Annotated[str, Query(description=BBOX_DESCRIPTION)],
        limit: Annotated[int, Query(ge=1, le=MAX_STATIONS)] = 2000,
    ) -> StationsResponse:
        box = parse_bbox(bbox)
        # Ask for one more than the limit to know whether the result was cut off.
        # The most powerful stations come first, so a cut-off list still shows what matters.
        rows = store.rows(
            """
            SELECT station_id, site_id, operator, display_name, lat, lon, n_points, n_hpc_points,
                   max_point_kw, plug_types, street, house_no, postcode, town, commissioned_on
            FROM stations
            WHERE lon BETWEEN $min_lon AND $max_lon AND lat BETWEEN $min_lat AND $max_lat
            ORDER BY max_point_kw DESC, station_id
            LIMIT $limit_plus_one
            """,
            {"min_lon": box[0], "min_lat": box[1], "max_lon": box[2], "max_lat": box[3],
             "limit_plus_one": limit + 1},
        )
        return StationsResponse(
            bbox=box, limit=limit, truncated=len(rows) > limit, stations=[Station(**r) for r in rows[:limit]]
        )

    @app.get("/operators", response_model=list[Operator], responses=NOT_READY, tags=["map"])
    def get_operators(
        store: Store,
        q: Annotated[str | None, Query(description="Case-insensitive substring of the operator name.")] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
    ) -> list[Operator]:
        rows = store.rows(
            """
            SELECT operator, n_stations, n_sites, n_points, n_hpc_points, hpc_kw FROM operators
            WHERE $q IS NULL OR contains(lower(operator), lower($q))
            ORDER BY n_points DESC, operator
            LIMIT $limit
            """,
            {"q": q, "limit": limit},
        )
        return [Operator(**r) for r in rows]

    @app.get("/plan", response_model=PlanResponse, responses=NOT_READY, tags=["planner"])
    def get_plan(
        store: Store,
        n: Annotated[int, Query(ge=1, le=50, description="Number of sites to place.")] = 10,
        radius_km: Annotated[
            float | None, Query(ge=5, le=100, description="Coverage radius; defaults to desert_radius_km.")
        ] = None,
    ) -> PlanResponse:
        coverage = coverage_config()
        radius = radius_km if radius_km is not None else float(coverage["desert_radius_km"])
        key = (n, radius)
        if key not in app.state.plan_cache:
            hexes = pd.DataFrame(store.rows(
                "SELECT cell, lat, lon, area_km2, nearest_hub_km FROM hexes WHERE res = $res",
                {"res": coverage["h3_resolutions"]["map"]},
            ))
            before = float(hexes.loc[hexes["nearest_hub_km"] > radius, "area_km2"].sum())
            plan = plan_sites(hexes, radius_km=radius, n=n)
            after = float(plan["desert_km2_remaining"].iloc[-1]) if len(plan) else before
            app.state.plan_cache[key] = PlanResponse(
                n=n,
                radius_km=radius,
                desert_km2_before=before,
                desert_km2_after=after,
                sites=[PlanSite(**r) for r in plan.to_dict(orient="records")],
            )
        return app.state.plan_cache[key]

    @app.get("/quality", response_model=QualityReport, responses=NOT_READY, tags=["data doctor"])
    def get_quality(store: Store) -> QualityReport:
        return QualityReport.model_validate(store.quality_report())


app = create_app()
