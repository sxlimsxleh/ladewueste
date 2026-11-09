"""Point-in-Germany test against data/ref/germany.geojson (Natural Earth 1:10m).

Even-odd ray casting: from each point, cast a ray towards +longitude and count how many
polygon edges it crosses. Odd = inside. Holes work automatically with even-odd counting,
so every ring of every polygon is treated the same way.

Vectorised with numpy over points (loop over ~3,200 edges, not over 100k+ points), so it
needs no geometry library. Treats lon/lat as planar, which is fine for an inside/outside test.
"""

import json
from pathlib import Path

import numpy as np

from pipeline.config import GERMANY_GEOJSON


def load_rings(path: Path = GERMANY_GEOJSON) -> list[np.ndarray]:
    """All rings (outer boundaries and holes) as arrays of shape (n, 2) in (lon, lat)."""
    geometry = json.loads(path.read_text(encoding="utf-8"))["features"][0]["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return [np.asarray(ring, dtype=float) for polygon in polygons for ring in polygon]


def points_in_germany(lat: np.ndarray, lon: np.ndarray, rings: list[np.ndarray] | None = None) -> np.ndarray:
    """Boolean array: True where (lat, lon) lies inside Germany. NaN coordinates -> False."""
    rings = load_rings() if rings is None else rings
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    inside = np.zeros(lat.shape, dtype=bool)
    for ring in rings:
        x1, y1 = ring[:-1, 0], ring[:-1, 1]
        x2, y2 = ring[1:, 0], ring[1:, 1]
        for ax, ay, bx, by in zip(x1, y1, x2, y2):
            # Does the horizontal line through the point cross this edge's latitude span?
            spans = (ay > lat) != (by > lat)
            # Longitude where the edge crosses that latitude (only meaningful where spans).
            with np.errstate(divide="ignore", invalid="ignore"):
                x_cross = ax + (lat - ay) * (bx - ax) / (by - ay)
            inside ^= spans & (lon < x_cross)
    return inside


KM_PER_DEGREE_LAT = 111.195


def distance_to_border_km(lat: float, lon: float, rings: list[np.ndarray] | None = None) -> float:
    """Shortest distance from one point to any boundary edge (not just to a vertex:
    the 1:10m vertices can be kilometres apart, so vertex distance overstates it).

    Uses a local equirectangular projection centred on the point: x = lon * cos(lat), y = lat.
    Accurate to well under 1% at the few-km scale we care about.
    """
    rings = load_rings() if rings is None else rings
    scale_x = KM_PER_DEGREE_LAT * np.cos(np.radians(lat))
    best = np.inf
    for ring in rings:
        # Edge endpoints in km, relative to the point (so the point is the origin).
        ax = (ring[:-1, 0] - lon) * scale_x
        ay = (ring[:-1, 1] - lat) * KM_PER_DEGREE_LAT
        bx = (ring[1:, 0] - lon) * scale_x
        by = (ring[1:, 1] - lat) * KM_PER_DEGREE_LAT
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        # Project the origin onto each edge, clamped to the segment.
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.clip(-(ax * dx + ay * dy) / length_sq, 0.0, 1.0)
        t = np.nan_to_num(t)  # zero-length edges
        px, py = ax + t * dx, ay + t * dy
        best = min(best, float(np.min(np.hypot(px, py))))
    return best
