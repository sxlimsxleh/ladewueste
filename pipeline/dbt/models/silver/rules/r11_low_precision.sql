-- R11: coordinates with few decimals. <= N decimals is flagged; whole degrees (~100 km) are unusable.
SELECT
    'R11' AS rule_id, p.record_no, p.station_id, NULL::INTEGER AS point_no, 'flagged' AS action,
    s.lat_raw || ' | ' || s.lon_raw AS before,
    p.coord_decimals || ' decimals' || CASE WHEN p.coord_decimals = 0 THEN ' (whole degrees, unusable)' ELSE '' END AS after
FROM {{ ref('parsed_records') }} AS p
JOIN {{ ref('stg_records') }} AS s USING (record_no)
WHERE p.coord_decimals <= {{ var('low_precision_decimals') }}
