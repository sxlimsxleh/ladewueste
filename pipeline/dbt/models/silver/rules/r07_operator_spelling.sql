-- R07: operator spellings that differ only in case, whitespace or '.'/',' -> most frequent spelling.
SELECT
    'R07' AS rule_id, p.record_no, p.station_id, NULL::INTEGER AS point_no, 'fixed' AS action,
    p.operator_clean AS before,
    o.surface_canonical AS after
FROM {{ ref('parsed_records') }} AS p
JOIN {{ ref('operator_map') }} AS o USING (operator_clean)
WHERE p.operator_clean <> o.surface_canonical
