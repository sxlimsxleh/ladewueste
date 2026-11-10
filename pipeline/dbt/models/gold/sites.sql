-- One row per site: stations of the same operator within site_radius_m of each other.
SELECT
    s.site_id,
    any_value(s.operator)              AS operator,
    avg(s.lat)                         AS lat,
    avg(s.lon)                         AS lon,
    count(*)                           AS n_stations,
    sum(s.n_points)                    AS n_points,
    sum(s.n_hpc_points)                AS n_hpc_points,
    max(s.max_point_kw)                AS max_point_kw,
    any_value(s.town)                  AS town,
    any_value(s.cell_map)              AS cell_map
FROM {{ ref('usable_stations') }} AS s
GROUP BY s.site_id
