"""Point-in-polygon and border distance, on a toy square and on the real boundary."""

import numpy as np
import pytest

from pipeline.germany import distance_to_border_km, points_in_germany

# A 1°x1° square with a 0.2° square hole, as (lon, lat) rings like GeoJSON.
SQUARE = np.array([[10.0, 50.0], [11.0, 50.0], [11.0, 51.0], [10.0, 51.0], [10.0, 50.0]])
HOLE = np.array([[10.4, 50.4], [10.6, 50.4], [10.6, 50.6], [10.4, 50.6], [10.4, 50.4]])


def test_square_with_hole() -> None:
    lat = np.array([50.2, 50.5, 52.0, np.nan])
    lon = np.array([10.2, 10.5, 10.5, 10.5])
    assert points_in_germany(lat, lon, [SQUARE, HOLE]).tolist() == [True, False, False, False]


def test_distance_to_edge_not_vertex() -> None:
    # 0.1° north of the middle of the top edge: ~11.1 km to the edge, ~57 km to the nearest corner.
    assert distance_to_border_km(51.1, 10.5, [SQUARE]) == pytest.approx(11.12, abs=0.05)


def test_real_boundary_known_cities() -> None:
    #                    Berlin  Munich  Paris   Vienna  Amsterdam
    lat = np.array([52.520, 48.137, 48.857, 48.208, 52.370])
    lon = np.array([13.405, 11.576, 2.352, 16.373, 4.895])
    assert points_in_germany(lat, lon).tolist() == [True, True, False, False, False]
