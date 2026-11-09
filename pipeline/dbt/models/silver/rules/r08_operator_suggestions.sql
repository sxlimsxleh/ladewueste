-- R08: names equal apart from the legal form, or fuzzy-similar. Suggested merge only;
-- applied ('fixed') only if a human approved it in seeds/operator_overrides.csv.
SELECT
    'R08' AS rule_id, p.record_no, p.station_id, NULL::INTEGER AS point_no,
    CASE WHEN o.approved THEN 'fixed' ELSE 'flagged' END AS action,
    o.surface_canonical AS before,
    o.suggested_target || ' (' || o.suggestion_reason || ' ' || round(o.suggestion_score)::INTEGER || ', '
        || CASE WHEN o.approved THEN 'approved' ELSE 'awaiting review' END || ')' AS after
FROM {{ ref('parsed_records') }} AS p
JOIN {{ ref('operator_map') }} AS o USING (operator_clean)
WHERE o.suggested_target IS NOT NULL
