"""Coverage model: sites, the H3 universe, nearest-HPC distance and the greedy planner.

All distances are great-circle (haversine) distances. BallTree with metric="haversine"
works in radians on (lat, lon) and returns angles; multiply by the earth radius for km.

Coverage rule (shared with the web app's play mode): a cell is covered by a site when the
cell's centre is within radius_km of the site, measured great-circle.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from pipeline.config import GERMANY_GEOJSON

EARTH_RADIUS_KM = 6371.0088


def to_radians(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    return np.radians(np.column_stack([lat, lon]))


# ---------------------------------------------------------------- sites


def group_sites(lat: np.ndarray, lon: np.ndarray, operator: np.ndarray, radius_m: float) -> np.ndarray:
    """Site number per station: stations of the same operator within radius_m of each other
    (directly or through a chain) form one site. Union-find over BallTree neighbour pairs."""
    n = len(lat)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]  # path halving keeps the trees flat
            i = parent[i]
        return i

    radius = radius_m / 1000 / EARTH_RADIUS_KM
    for op in pd.unique(operator):
        idx = np.where(operator == op)[0]
        if len(idx) < 2:
            continue
        tree = BallTree(to_radians(lat[idx], lon[idx]), metric="haversine")
        for i, neighbours in zip(idx, tree.query_radius(to_radians(lat[idx], lon[idx]), r=radius)):
            for j in idx[neighbours]:
                root_i, root_j = find(i), find(int(j))
                if root_i != root_j:
                    parent[max(root_i, root_j)] = min(root_i, root_j)
    roots = np.array([find(i) for i in range(n)])
    # Renumber roots to 0..k-1 in order of first appearance, so site numbers are compact.
    _, site = np.unique(roots, return_inverse=True)
    return site


# ---------------------------------------------------------------- universe and distances


def germany_cells(res: int, path: Path = GERMANY_GEOJSON) -> pd.DataFrame:
    """All H3 cells at `res` whose centre lies inside Germany, with centre and area."""
    geometry = json.loads(path.read_text(encoding="utf-8"))["features"][0]["geometry"]
    cells = sorted(h3.h3shape_to_cells(h3.geo_to_h3shape(geometry), res))
    centres = np.array([h3.cell_to_latlng(c) for c in cells])
    return pd.DataFrame({
        "cell": cells,
        "res": res,
        "lat": centres[:, 0],
        "lon": centres[:, 1],
        "area_km2": [h3.cell_area(c, "km^2") for c in cells],
    })


def nearest_km(lat: np.ndarray, lon: np.ndarray, target_lat: np.ndarray, target_lon: np.ndarray) -> np.ndarray:
    """Great-circle distance from each point to its nearest target, in km."""
    if len(target_lat) == 0:
        return np.full(len(lat), np.inf)
    tree = BallTree(to_radians(target_lat, target_lon), metric="haversine")
    distance, _ = tree.query(to_radians(lat, lon), k=1)
    return distance[:, 0] * EARTH_RADIUS_KM


# ---------------------------------------------------------------- planner


@dataclass
class Pick:
    rank: int
    candidate: int            # index into the candidate list
    desert_km2_removed: float
    desert_km2_remaining: float


def greedy_cover(covers: list[np.ndarray], area_km2: np.ndarray, n: int) -> list[Pick]:
    """Generic greedy maximum coverage.

    covers[c] = indices of the desert cells candidate c would cover; area_km2[i] = area of
    desert cell i. Each round picks the candidate covering the most still-uncovered km²
    (ties: lowest candidate index, so results are deterministic), then marks those cells
    covered. Stops early when no candidate removes any desert.
    """
    uncovered = np.ones(len(area_km2), dtype=bool)
    remaining = float(area_km2.sum())
    picks: list[Pick] = []
    for rank in range(1, n + 1):
        gains = np.array([area_km2[cells][uncovered[cells]].sum() for cells in covers])
        if len(gains) == 0 or gains.max() <= 0:
            break
        best = int(np.argmax(gains))  # argmax returns the first maximum -> lowest index wins ties
        uncovered[covers[best]] = False
        remaining -= float(gains[best])
        picks.append(Pick(rank, best, float(gains[best]), max(remaining, 0.0)))
    return picks


def plan_sites(hexes: pd.DataFrame, radius_km: float, n: int) -> pd.DataFrame:
    """Greedy HPC hub plan on a hex table (columns cell, lat, lon, area_km2, nearest_hub_km).

    Desert = nearest_hub_km > radius_km. Candidates are the desert cells themselves; each
    covers the desert cells whose centre is within radius_km of its centre.
    """
    desert = hexes[hexes["nearest_hub_km"] > radius_km].sort_values("cell").reset_index(drop=True)
    columns = ["rank", "cell", "lat", "lon", "desert_km2_removed", "desert_km2_remaining"]
    if desert.empty:
        return pd.DataFrame(columns=columns)
    points = to_radians(desert["lat"].to_numpy(), desert["lon"].to_numpy())
    covers = BallTree(points, metric="haversine").query_radius(points, r=radius_km / EARTH_RADIUS_KM)
    picks = greedy_cover(list(covers), desert["area_km2"].to_numpy(), n)
    return pd.DataFrame(
        [
            (p.rank, desert.at[p.candidate, "cell"], desert.at[p.candidate, "lat"], desert.at[p.candidate, "lon"],
             p.desert_km2_removed, p.desert_km2_remaining)
            for p in picks
        ],
        columns=columns,
    )
