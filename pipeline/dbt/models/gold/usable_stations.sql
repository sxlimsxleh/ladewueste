-- Usable stations only (silver.stations.usable_for_coverage), with site and H3 cells.
SELECT
    s.station_id,
    g.site_id,
    s.operator,
    s.display_name,
    s.register_type,
    s.n_points,
    s.n_hpc_points,
    s.max_point_kw,
    s.station_kw,
    s.plug_types,
    s.commissioned_on,
    s.street, s.house_no, s.postcode, s.town, s.state,
    s.lat,
    s.lon,
    g.cell_map,
    g.cell_detail
FROM {{ ref('stations') }} AS s
JOIN {{ ref('station_geo') }} AS g USING (station_id)
