-- is_desert is exactly "nearest hub farther than desert_radius_km", and distances are sane:
-- a hub is an HPC point too, so the nearest HPC point can never be farther than the nearest hub.
SELECT res, cell, nearest_hpc_km, nearest_hub_km, is_desert FROM {{ ref('hexes') }}
WHERE is_desert <> (nearest_hub_km > {{ var('desert_radius_km') }})
   OR nearest_hpc_km < 0
   OR nearest_hpc_km > nearest_hub_km + 0.001
