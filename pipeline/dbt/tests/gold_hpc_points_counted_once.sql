-- Every usable HPC point is counted exactly once per resolution: either in a universe cell
-- or (near the border) in a cell whose centre is outside Germany. Nothing lost, nothing doubled.
{%- set levels = [('map', var('h3_res_map')), ('detail', var('h3_res_detail'))] %}
{% for name, res in levels %}
SELECT {{ res }} AS res, in_hexes, outside_universe, all_hpc FROM (
    SELECT
        (SELECT sum(n_hpc_points) FROM {{ ref('hexes') }} WHERE res = {{ res }}) AS in_hexes,
        (SELECT count(*) FROM {{ ref('points') }} AS p
          WHERE p.is_hpc AND p.cell_{{ name }} NOT IN (SELECT cell FROM {{ ref('hex_universe') }} WHERE res = {{ res }})) AS outside_universe,
        (SELECT count(*) FROM {{ ref('points') }} WHERE is_hpc) AS all_hpc
)
WHERE in_hexes + outside_universe <> all_hpc
{% if not loop.last %}UNION ALL{% endif %}
{% endfor %}
