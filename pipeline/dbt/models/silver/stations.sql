-- One row per register record (charging device), cleaned and typed, with every flag.
-- Nothing is dropped: usable_for_coverage decides what the coverage model may use.
WITH flags AS (
    SELECT record_no, list_sort(list_distinct(list(rule_id))) AS flags
    FROM {{ ref('rule_findings') }}
    WHERE action = 'flagged'
    GROUP BY record_no
),
points AS (
    SELECT
        record_no,
        count(*)                          AS n_points,
        max(power_kw)                     AS max_point_kw,
        count(*) FILTER (WHERE is_hpc)    AS n_hpc_points,
        list_sort(list_distinct(flatten(list(plug_types)))) AS plug_types
    FROM {{ ref('charging_points') }}
    GROUP BY record_no
)
SELECT
    p.station_id,
    p.record_no,
    o.operator_canonical                       AS operator,
    p.operator_clean                           AS operator_as_registered,
    p.display_name,
    p.status,
    p.register_type,
    pt.n_points,
    p.station_kw,
    pt.max_point_kw,
    pt.n_hpc_points,
    pt.plug_types,
    p.commissioned_on,
    p.street, p.house_no, p.address_extra, p.postcode, p.town, p.district, p.state,
    c.lat,
    c.lon,
    c.coord_status,
    c.border_km,
    p.coord_decimals,
    ph.record_no IS NOT NULL                   AS is_placeholder_coord,
    d.duplicate_of,
    coalesce(f.flags, []::VARCHAR[])           AS flags,
    c.coord_status IN ('inside', 'swapped', 'border_tolerance')
        AND ph.record_no IS NULL
        AND p.coord_decimals > 0
        AND d.duplicate_of IS NULL             AS usable_for_coverage
FROM {{ ref('parsed_records') }} AS p
JOIN {{ ref('coord_checks') }} AS c USING (record_no)
LEFT JOIN {{ ref('operator_map') }} AS o USING (operator_clean)
LEFT JOIN points AS pt USING (record_no)
LEFT JOIN {{ ref('r10_placeholder_coords') }} AS ph USING (record_no)
LEFT JOIN {{ ref('r13_duplicates') }} AS d USING (record_no)
LEFT JOIN flags AS f USING (record_no)
