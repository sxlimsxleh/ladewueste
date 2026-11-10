-- One row per usable charging point, with everything the API needs to re-aggregate
-- hexes for a power-class or operator filter.
SELECT
    c.station_id,
    c.point_no,
    s.site_id,
    s.operator,
    c.power_kw,
    c.is_hpc,
    c.plug_types,
    c.current_types,
    s.lat,
    s.lon,
    s.cell_map,
    s.cell_detail
FROM {{ ref('charging_points') }} AS c
JOIN {{ ref('usable_stations') }} AS s USING (station_id)
