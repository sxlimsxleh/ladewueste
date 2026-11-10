"""Site grouping and H3 cells for every usable station.
Thin dbt wrapper; the logic (and its unit tests) live in pipeline/geo.py."""

import h3

from pipeline.geo import group_sites


def model(dbt, session):
    dbt.config(materialized="table")
    radius_m = float(dbt.config.get("site_radius_m"))
    res_map = int(dbt.config.get("h3_res_map"))
    res_detail = int(dbt.config.get("h3_res_detail"))

    df = (
        dbt.ref("stations")
        .filter("usable_for_coverage")
        .project("station_id, operator, lat, lon")
        .order("station_id")
        .df()
    )
    site_no = group_sites(df["lat"].to_numpy(), df["lon"].to_numpy(), df["operator"].to_numpy(), radius_m)
    # A site is named after its lowest station_id, which is stable across runs.
    df["site_no"] = site_no
    df["site_id"] = df.groupby("site_no")["station_id"].transform(lambda ids: min(ids, key=int))
    df["cell_map"] = [h3.latlng_to_cell(la, lo, res_map) for la, lo in zip(df["lat"], df["lon"])]
    df["cell_detail"] = [h3.latlng_to_cell(la, lo, res_detail) for la, lo in zip(df["lat"], df["lon"])]
    return df[["station_id", "site_id", "cell_map", "cell_detail"]]
