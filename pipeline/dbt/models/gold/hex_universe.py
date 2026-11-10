"""Coverage universe: H3 cells whose centre lies inside Germany, at the map and detail
resolution, with great-circle distances from each cell centre to
  - the nearest HPC point (any charging point >= hpc_threshold_kw), shown in the side panel
  - the nearest HPC hub (a site with >= hub_min_hpc_points HPC points), which decides deserts.
Thin dbt wrapper; the logic (and its unit tests) live in pipeline/geo.py."""

import pandas as pd

from pipeline.geo import germany_cells, nearest_km


def model(dbt, session):
    dbt.config(materialized="table")
    resolutions = [int(dbt.config.get("h3_res_map")), int(dbt.config.get("h3_res_detail"))]
    hub_min = int(dbt.config.get("hub_min_hpc_points"))
    hpc = dbt.ref("points").filter("is_hpc").aggregate("lat, lon", "lat, lon").df()
    # Hub distance is measured to the hub's own HPC points, not to the site's centre: a site can
    # stretch over hundreds of metres, and its average position may not be where any charger is.
    hub_sites = dbt.ref("sites").filter(f"n_hpc_points >= {hub_min}").project("site_id")
    hubs = (
        dbt.ref("points").filter("is_hpc")
        .join(hub_sites, "site_id")
        .aggregate("lat, lon", "lat, lon")
        .df()
    )

    frames = []
    for res in resolutions:
        cells = germany_cells(res)
        lat, lon = cells["lat"].to_numpy(), cells["lon"].to_numpy()
        cells["nearest_hpc_km"] = nearest_km(lat, lon, hpc["lat"].to_numpy(), hpc["lon"].to_numpy())
        cells["nearest_hub_km"] = nearest_km(lat, lon, hubs["lat"].to_numpy(), hubs["lon"].to_numpy())
        frames.append(cells)
    return pd.concat(frames, ignore_index=True)
