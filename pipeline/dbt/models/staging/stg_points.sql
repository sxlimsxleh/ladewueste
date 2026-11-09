-- R02 (unpivot): the register stores up to N charging points per record in N groups of
-- wide columns. One row per filled group. Values are still raw text.
{% for n in range(1, var('n_point_groups') + 1) %}
SELECT
    record_no,
    station_id,
    {{ n }}                AS point_no,
    p{{ n }}_plugs_raw     AS plugs_raw,
    p{{ n }}_kw_raw        AS kw_raw,
    p{{ n }}_evse_raw      AS evse_raw
FROM {{ ref('stg_records') }}
WHERE p{{ n }}_plugs_raw IS NOT NULL OR p{{ n }}_kw_raw IS NOT NULL
{% if not loop.last %}UNION ALL{% endif %}
{% endfor %}
