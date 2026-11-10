"""A tiny synthetic gold folder, so the API tests need no download and run in CI.

Three res-6 cells around (52, 10) and one res-7 cell:
  cell_a  desert   (nearest hub 40 km), one EnBW 150 kW HPC point
  cell_b  covered  (nearest hub 5 km),  one Tesla 300 kW HPC point + one EnBW 22 kW point
  cell_c  desert   (nearest hub 30 km), no points
"""

import json
from pathlib import Path

import duckdb
import h3
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app.main import create_app
from pipeline.config import load_config

COVERAGE = load_config()["coverage"]
RES_MAP = COVERAGE["h3_resolutions"]["map"]
RES_DETAIL = COVERAGE["h3_resolutions"]["detail"]

CELL_B = h3.latlng_to_cell(52.0, 10.0, RES_MAP)
CELL_A, CELL_C = sorted(h3.grid_ring(CELL_B, 1))[:2]


def centre(cell: str) -> tuple[float, float]:
    return h3.cell_to_latlng(cell)


def hex_row(cell: str, res: int, nearest_hub_km: float, n_points: int = 0) -> dict:
    lat, lon = centre(cell)
    return {
        "res": res, "cell": cell, "lat": lat, "lon": lon, "area_km2": h3.cell_area(cell, "km^2"),
        "n_stations": n_points, "n_sites": n_points, "n_points": n_points, "total_kw": 0.0,
        "n_hpc_points": 0, "hpc_kw": 0.0, "top_operators": [],
        "nearest_hpc_km": min(nearest_hub_km, 10.0), "nearest_hub_km": nearest_hub_km,
        "is_desert": nearest_hub_km > COVERAGE["desert_radius_km"],
    }


def station(station_id: str, operator: str, cell: str, kw: float, n_hpc: int) -> dict:
    lat, lon = centre(cell)
    return {
        "station_id": station_id, "site_id": station_id, "operator": operator, "display_name": None,
        "register_type": "Schnellladeeinrichtung", "n_points": 1, "n_hpc_points": n_hpc,
        "max_point_kw": kw, "station_kw": kw, "plug_types": ["CCS"], "commissioned_on": pd.Timestamp("2024-05-01").date(),
        "street": "Teststraße", "house_no": "1", "postcode": "38100", "town": "Testdorf", "state": "Niedersachsen",
        "lat": lat, "lon": lon, "cell_map": cell, "cell_detail": h3.latlng_to_cell(lat, lon, RES_DETAIL),
    }


def write_gold(gold: Path) -> None:
    stations = pd.DataFrame([
        station("1", "EnBW", CELL_A, 150.0, 1),
        station("2", "Tesla", CELL_B, 300.0, 1),
        station("3", "EnBW", CELL_B, 22.0, 0),
    ])
    points = stations[["station_id", "site_id", "operator", "lat", "lon", "cell_map", "cell_detail"]].copy()
    points["point_no"] = 1
    points["power_kw"] = stations["max_point_kw"]
    points["is_hpc"] = points["power_kw"] >= COVERAGE["hpc_threshold_kw"]
    points["plug_types"] = [["CCS"], ["CCS"], ["Type 2"]]
    points["current_types"] = [["DC"], ["DC"], ["AC"]]
    hexes = pd.DataFrame([
        hex_row(CELL_A, RES_MAP, 40.0, 1),
        hex_row(CELL_B, RES_MAP, 5.0, 2),
        hex_row(CELL_C, RES_MAP, 30.0),
        hex_row(stations.loc[0, "cell_detail"], RES_DETAIL, 40.0, 1),
    ])
    sites = stations[["site_id", "operator", "lat", "lon", "n_hpc_points"]]
    operators = pd.DataFrame([
        {"operator": "EnBW", "n_stations": 2, "n_sites": 2, "n_points": 2, "n_hpc_points": 1,
         "total_kw": 172.0, "hpc_kw": 150.0, "share_of_hpc_points_pct": 50.0},
        {"operator": "Tesla", "n_stations": 1, "n_sites": 1, "n_points": 1, "n_hpc_points": 1,
         "total_kw": 300.0, "hpc_kw": 300.0, "share_of_hpc_points_pct": 50.0},
    ])
    con = duckdb.connect()
    for name, frame in {"hexes": hexes, "points": points, "stations": stations, "sites": sites,
                        "operators": operators}.items():
        con.register("frame", frame)
        con.execute(f"COPY frame TO '{gold / name}.parquet' (FORMAT parquet)")
        con.unregister("frame")
    con.close()

    report = {
        "generated_at": "2026-11-10T12:00:00Z",
        "source": {"file": "test.csv", "sha256": "abc", "licence": "CC BY 4.0", "attribution": "Bundesnetzagentur.de"},
        "funnel": {"raw_records": 4, "stations": 4, "stations_usable": 3, "stations_duplicate": 1,
                   "operators_as_registered": 3, "operators_canonical": 2, "charging_points": 4,
                   "charging_points_usable": 3, "hpc_points_usable": 2},
        "rules": [{
            "rule_id": "R13", "title": "Duplicate records", "why": "Counted twice otherwise.", "model": "r13_duplicates",
            "rows_affected": 1, "finding_rows": 1, "actions": {"flagged": 1},
            "examples": [{"station_id": "4", "point_no": None, "action": "flagged",
                          "before": "station 4", "after": "duplicate_of 2"}],
        }],
    }
    (gold / "quality_report.json").write_text(json.dumps(report), encoding="utf-8")


@pytest.fixture(scope="session")
def gold_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    gold = tmp_path_factory.mktemp("gold")
    write_gold(gold)
    return gold


@pytest.fixture(scope="session")
def client(gold_dir: Path) -> TestClient:
    return TestClient(create_app(gold_dir))
