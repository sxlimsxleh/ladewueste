"""API behaviour on the synthetic gold folder from conftest.py."""

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app
from api.export_openapi import OPENAPI_PATH, openapi_json
from api.tests.conftest import CELL_A, CELL_B, CELL_C, COVERAGE, RES_DETAIL, RES_MAP
from pipeline.geo import plan_sites


def hexes_by_cell(response_json: dict) -> dict[str, dict]:
    return {h["cell"]: h for h in response_json["hexes"]}


def test_config_comes_from_config_yaml(client: TestClient) -> None:
    body = client.get("/config").json()
    assert body["desert_radius_km"] == COVERAGE["desert_radius_km"]
    assert body["hub_min_hpc_points"] == COVERAGE["hub_min_hpc_points"]
    assert (body["h3_res_map"], body["h3_res_detail"]) == (RES_MAP, RES_DETAIL)
    assert body["attribution"] == "Bundesnetzagentur.de"


def test_hexes_unfiltered(client: TestClient) -> None:
    body = client.get("/hexes", params={"res": RES_MAP}).json()
    cells = hexes_by_cell(body)
    assert set(cells) == {CELL_A, CELL_B, CELL_C}
    assert cells[CELL_B]["n_points"] == 2
    assert cells[CELL_B]["n_hpc_points"] == 1
    assert cells[CELL_B]["hpc_kw"] == 300.0
    assert cells[CELL_B]["top_operators"] == ["EnBW", "Tesla"]  # tie on count -> alphabetical
    assert [cells[c]["is_desert"] for c in (CELL_A, CELL_B, CELL_C)] == [True, False, True]
    assert body["desert_km2"] == pytest.approx(cells[CELL_A]["area_km2"] + cells[CELL_C]["area_km2"])


def test_filters_change_counts_but_never_deserts(client: TestClient) -> None:
    unfiltered = hexes_by_cell(client.get("/hexes", params={"res": RES_MAP}).json())
    by_kw = hexes_by_cell(client.get("/hexes", params={"res": RES_MAP, "min_kw": 200}).json())
    by_operator = hexes_by_cell(client.get("/hexes", params={"res": RES_MAP, "operator": "EnBW"}).json())

    assert by_kw[CELL_B]["n_points"] == 1 and by_kw[CELL_B]["top_operators"] == ["Tesla"]
    assert by_kw[CELL_A]["n_points"] == 0  # 150 kW < 200 kW
    assert by_operator[CELL_B]["n_points"] == 1 and by_operator[CELL_B]["hpc_kw"] == 0.0
    for filtered in (by_kw, by_operator):
        for cell, original in unfiltered.items():
            assert filtered[cell]["is_desert"] == original["is_desert"]
            assert filtered[cell]["nearest_hub_km"] == original["nearest_hub_km"]


def test_detail_resolution_needs_bbox(client: TestClient) -> None:
    assert client.get("/hexes", params={"res": RES_DETAIL}).status_code == 422
    body = client.get("/hexes", params={"res": RES_DETAIL, "bbox": "9,51,11,53"}).json()
    assert len(body["hexes"]) == 1 and body["hexes"][0]["n_points"] == 1
    empty = client.get("/hexes", params={"res": RES_DETAIL, "bbox": "0,0,1,1"}).json()
    assert empty["hexes"] == [] and empty["total_km2"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {"res": 5},
        {"res": RES_MAP, "min_kw": -1},
        {"res": RES_MAP, "bbox": "1,2,3"},
        {"res": RES_MAP, "bbox": "a,b,c,d"},
        {"res": RES_MAP, "bbox": "11,51,9,53"},  # min > max
    ],
)
def test_hexes_rejects_bad_parameters(client: TestClient, params: dict) -> None:
    assert client.get("/hexes", params=params).status_code == 422


def test_stations_in_bbox_and_truncation(client: TestClient) -> None:
    body = client.get("/stations", params={"bbox": "9,51,11,53"}).json()
    assert {s["station_id"] for s in body["stations"]} == {"1", "2", "3"}
    assert body["truncated"] is False

    top = client.get("/stations", params={"bbox": "9,51,11,53", "limit": 1}).json()
    assert top["truncated"] is True
    assert [s["station_id"] for s in top["stations"]] == ["2"]  # most powerful first
    assert client.get("/stations").status_code == 422  # bbox required


def test_operators_search(client: TestClient) -> None:
    assert [o["operator"] for o in client.get("/operators").json()] == ["EnBW", "Tesla"]
    assert [o["operator"] for o in client.get("/operators", params={"q": "TES"}).json()] == ["Tesla"]


def test_plan_matches_pipeline_planner(client: TestClient, gold_dir: Path) -> None:
    body = client.get("/plan", params={"n": 3}).json()
    hexes = duckdb.sql(f"SELECT * FROM '{gold_dir / 'hexes.parquet'}' WHERE res = {RES_MAP}").df()
    expected = plan_sites(hexes, radius_km=COVERAGE["desert_radius_km"], n=3)

    assert [s["cell"] for s in body["sites"]] == expected["cell"].tolist()
    assert body["radius_km"] == COVERAGE["desert_radius_km"]
    assert body["desert_km2_before"] == pytest.approx(hexes.loc[hexes["is_desert"], "area_km2"].sum())
    assert body["desert_km2_after"] == pytest.approx(0.0, abs=1e-6)  # neighbouring cells: one site covers both


def test_plan_radius_changes_the_desert(client: TestClient) -> None:
    # With a 35 km radius only cell A (40 km from a hub) is still desert.
    body = client.get("/plan", params={"n": 5, "radius_km": 35}).json()
    assert [s["cell"] for s in body["sites"]] == [CELL_A]


@pytest.mark.parametrize("params", [{"n": 0}, {"n": 51}, {"radius_km": 1}, {"radius_km": 500}])
def test_plan_rejects_bad_parameters(client: TestClient, params: dict) -> None:
    assert client.get("/plan", params=params).status_code == 422


def test_quality_report(client: TestClient) -> None:
    body = client.get("/quality").json()
    assert body["funnel"]["stations_usable"] == 3
    assert body["rules"][0]["examples"][0]["after"] == "duplicate_of 2"


def test_missing_gold_data_gives_503(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.get("/hexes", params={"res": RES_MAP})
    assert response.status_code == 503
    assert "make pipeline" in response.json()["detail"]
    assert client.get("/config").status_code == 200  # config needs no gold data


def test_large_responses_are_gzipped(client: TestClient) -> None:
    # GZipMiddleware compresses responses over 1,000 bytes; the synthetic hexes are smaller,
    # so the OpenAPI document stands in for a large response.
    response = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"


def test_committed_openapi_is_up_to_date() -> None:
    """The web app's TypeScript types are generated from api/openapi.json. If this fails,
    the API changed without regenerating the contract: run `make types`."""
    assert OPENAPI_PATH.read_text(encoding="utf-8") == openapi_json()


def test_root_redirects_to_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
