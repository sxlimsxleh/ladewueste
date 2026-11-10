"""Coverage model: sites, nearest distance and the greedy planner on tiny synthetic inputs."""

import h3
import numpy as np
import pandas as pd
import pytest

from pipeline.geo import (
    EARTH_RADIUS_KM,
    greedy_cover,
    group_sites,
    nearest_km,
    plan_sites,
)

# One degree of latitude in metres, to place test points at exact distances.
M_PER_DEG_LAT = np.radians(1) * EARTH_RADIUS_KM * 1000


def test_sites_group_same_operator_within_radius() -> None:
    lat = np.array([50.0, 50.0 + 19 / M_PER_DEG_LAT, 50.0 + 40 / M_PER_DEG_LAT, 50.0])
    lon = np.array([10.0, 10.0, 10.0, 10.0])
    operator = np.array(["A", "A", "A", "B"])
    site = group_sites(lat, lon, operator, radius_m=20)
    # 0-1 are 19 m apart, 1-2 are 21 m apart: 0 and 1 form a site, 2 is alone.
    # 3 sits on top of 0 but belongs to another operator, so it is its own site.
    assert site[0] == site[1]
    assert len({site[0], site[2], site[3]}) == 3


def test_sites_chain_through_neighbours() -> None:
    # 0-1 and 1-2 are 15 m apart (0-2 is 30 m): one site through the chain.
    lat = 50.0 + np.array([0, 15, 30]) / M_PER_DEG_LAT
    site = group_sites(lat, np.full(3, 10.0), np.array(["A", "A", "A"]), radius_m=20)
    assert len(set(site)) == 1


def test_nearest_km() -> None:
    # One degree of latitude ≈ 111.2 km.
    distance = nearest_km(np.array([50.0, 52.0]), np.array([10.0, 10.0]), np.array([51.0, 53.5]), np.array([10.0, 10.0]))
    assert distance == pytest.approx([111.2, 111.2], abs=0.1)
    assert np.isinf(nearest_km(np.array([50.0]), np.array([10.0]), np.array([]), np.array([]))).all()


def test_greedy_cover_picks_biggest_gain_first_and_stops_when_done() -> None:
    #   cells:      0    1    2    3    4
    area = np.array([1.0, 1.0, 1.0, 5.0, 1.0])
    covers = [
        np.array([0, 1, 2]),  # candidate 0: 3 km²
        np.array([3]),        # candidate 1: 5 km²  -> best first
        np.array([2, 3, 4]),  # candidate 2: 7 km² at first, but only 2 km² once cell 3 is covered
        np.array([0, 1]),     # candidate 3
    ]
    picks = greedy_cover(covers, area, n=10)
    assert [p.candidate for p in picks] == [2, 0]
    assert [p.desert_km2_removed for p in picks] == [7.0, 2.0]
    assert picks[-1].desert_km2_remaining == 0.0
    assert len(picks) == 2  # stopped early: nothing left to cover


def test_greedy_cover_breaks_ties_by_lowest_index() -> None:
    picks = greedy_cover([np.array([0]), np.array([1])], np.array([1.0, 1.0]), n=1)
    assert picks[0].candidate == 0


def test_plan_sites_on_h3_grid() -> None:
    # A small H3 patch: a centre cell and two rings around it, all desert except the centre.
    centre = h3.latlng_to_cell(52.0, 10.0, 6)
    cells = sorted(h3.grid_disk(centre, 2))
    hexes = pd.DataFrame({
        "cell": cells,
        "lat": [h3.cell_to_latlng(c)[0] for c in cells],
        "lon": [h3.cell_to_latlng(c)[1] for c in cells],
        "area_km2": [h3.cell_area(c, "km^2") for c in cells],
        "nearest_hub_km": [0.0 if c == centre else 99.0 for c in cells],
    })
    total_desert = hexes.loc[hexes["nearest_hub_km"] > 25, "area_km2"].sum()

    plan = plan_sites(hexes, radius_km=25, n=5)
    # The patch is ~26 km across, so a single well-placed site within 25 km covers all of it;
    # the greedy planner must find that and stop. Candidates are desert cells only.
    assert len(plan) == 1
    assert plan.loc[0, "desert_km2_removed"] == pytest.approx(total_desert)
    assert plan.loc[0, "cell"] != centre

    # With a tiny radius each pick covers only itself: n picks, one cell each.
    small = plan_sites(hexes, radius_km=1, n=3)
    assert len(small) == 3
    assert small["desert_km2_removed"].tolist() == pytest.approx(
        hexes.set_index("cell").loc[small["cell"], "area_km2"].tolist()
    )


def test_plan_sites_without_desert_is_empty() -> None:
    hexes = pd.DataFrame({"cell": ["a"], "lat": [50.0], "lon": [10.0], "area_km2": [36.0], "nearest_hub_km": [3.0]})
    assert plan_sites(hexes, radius_km=25, n=10).empty
