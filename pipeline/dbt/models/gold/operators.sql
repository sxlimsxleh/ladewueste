-- One row per canonical operator (usable stations only), for the map's operator filter.
SELECT
    p.operator,
    count(DISTINCT p.station_id)                       AS n_stations,
    count(DISTINCT p.site_id)                          AS n_sites,
    count(*)                                           AS n_points,
    count(*) FILTER (WHERE p.is_hpc)                   AS n_hpc_points,
    sum(p.power_kw)                                    AS total_kw,
    coalesce(sum(p.power_kw) FILTER (WHERE p.is_hpc), 0) AS hpc_kw,
    round(100.0 * count(*) FILTER (WHERE p.is_hpc)
          / sum(count(*) FILTER (WHERE p.is_hpc)) OVER (), 2) AS share_of_hpc_points_pct
FROM {{ ref('points') }} AS p
GROUP BY p.operator
