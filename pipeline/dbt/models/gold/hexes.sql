-- One row per H3 cell (map and detail resolution) whose centre lies in Germany.
-- Elevation on the map = hpc_kw; colour = nearest_hub_km.
-- Desert = no HPC hub (site with >= hub_min_hpc_points HPC points) within desert_radius_km.
{%- set levels = [('map', var('h3_res_map')), ('detail', var('h3_res_detail'))] %}
WITH by_cell AS (
    {% for name, res in levels %}
    SELECT {{ res }} AS res, cell_{{ name }} AS cell, * EXCLUDE (cell_map, cell_detail)
    FROM {{ ref('points') }}
    {% if not loop.last %}UNION ALL{% endif %}
    {% endfor %}
),
totals AS (
    SELECT
        res, cell,
        count(DISTINCT station_id)                     AS n_stations,
        count(DISTINCT site_id)                        AS n_sites,
        count(*)                                       AS n_points,
        sum(power_kw)                                  AS total_kw,
        count(*) FILTER (WHERE is_hpc)                 AS n_hpc_points,
        coalesce(sum(power_kw) FILTER (WHERE is_hpc), 0) AS hpc_kw
    FROM by_cell
    GROUP BY res, cell
),
top_operators AS (
    -- The three operators with the most charging points in the cell.
    SELECT res, cell, list(operator ORDER BY n DESC, operator)[1:3] AS top_operators
    FROM (SELECT res, cell, operator, count(*) AS n FROM by_cell GROUP BY ALL)
    GROUP BY res, cell
)
SELECT
    u.res,
    u.cell,
    u.lat,
    u.lon,
    u.area_km2,
    coalesce(t.n_stations, 0)      AS n_stations,
    coalesce(t.n_sites, 0)         AS n_sites,
    coalesce(t.n_points, 0)        AS n_points,
    coalesce(t.total_kw, 0)        AS total_kw,
    coalesce(t.n_hpc_points, 0)    AS n_hpc_points,
    coalesce(t.hpc_kw, 0)          AS hpc_kw,
    coalesce(o.top_operators, []::VARCHAR[]) AS top_operators,
    u.nearest_hpc_km,
    u.nearest_hub_km,
    u.nearest_hub_km > {{ var('desert_radius_km') }} AS is_desert
FROM {{ ref('hex_universe') }} AS u
LEFT JOIN totals AS t USING (res, cell)
LEFT JOIN top_operators AS o USING (res, cell)
