-- One row per charging point (R02 unpivot) with:
--   R03 plug labels -> normalised plug types (via seed plug_type_map)
--   R04 one kW value per plug; the point's power is the max of its list
--   R12 EVSE-ID cells -> list of valid IDs; anything else kept aside as invalid
WITH points AS (
    SELECT
        *,
        {{ split_list('plugs_raw') }} AS plug_labels,
        list_transform({{ split_list('kw_raw') }}, lambda x: {{ german_decimal('x') }}) AS kw_values,
        list_filter(
            list_transform(regexp_split_to_array(coalesce(evse_raw, ''), '[;\s]+'), lambda x: upper(x)),
            lambda x: x <> ''
        ) AS evse_tokens
    FROM {{ ref('stg_points') }}
),

plug_types AS (
    -- Unnest the labels, map each through the seed, and collect the distinct types back.
    SELECT
        record_no,
        point_no,
        list_sort(list_distinct(list(m.plug_type))) AS plug_types,
        list_sort(list_distinct(list(m.current_type))) AS current_types,
        count(*) FILTER (WHERE m.plug_type IS NULL) AS n_unknown_labels
    FROM (SELECT record_no, point_no, unnest(plug_labels) AS label FROM points) AS l
    LEFT JOIN {{ ref('plug_type_map') }} AS m ON m.raw_label = l.label
    GROUP BY record_no, point_no
)

SELECT
    p.station_id,
    p.record_no,
    p.point_no,
    p.plugs_raw,
    p.plug_labels,
    coalesce(t.plug_types, []::VARCHAR[])   AS plug_types,
    coalesce(t.current_types, []::VARCHAR[]) AS current_types,
    coalesce(t.n_unknown_labels, 0)          AS n_unknown_labels,
    p.kw_raw,
    p.kw_values,
    list_max(p.kw_values)                    AS power_kw,
    len(p.plug_labels) <> len(p.kw_values)   AS kw_list_mismatch,
    list_max(p.kw_values) = 0
        OR list_max(p.kw_values) > {{ var('max_plausible_point_kw') }} AS power_implausible,
    list_max(p.kw_values) >= {{ var('hpc_threshold_kw') }} AS is_hpc,
    p.evse_raw,
    list_filter(p.evse_tokens, lambda x: regexp_full_match(x, {{ evse_pattern() }}))     AS evse_ids,
    list_filter(p.evse_tokens, lambda x: NOT regexp_full_match(x, {{ evse_pattern() }})) AS evse_invalid_tokens
FROM points AS p
LEFT JOIN plug_types AS t USING (record_no, point_no)
