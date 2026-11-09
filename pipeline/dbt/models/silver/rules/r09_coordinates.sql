-- R09: coordinates not plainly inside Germany.
--   swapped          -> fixed (lat/lon swapped back)
--   border_tolerance -> accepted (within tolerance of the generalised 1:10m border)
--   outside, missing -> flagged
SELECT
    'R09' AS rule_id, c.record_no, p.station_id, NULL::INTEGER AS point_no,
    CASE c.coord_status WHEN 'swapped' THEN 'fixed' WHEN 'border_tolerance' THEN 'accepted' ELSE 'flagged' END AS action,
    concat_ws(', ', p.lat_parsed::VARCHAR, p.lon_parsed::VARCHAR) || ' (' || coalesce(p.town, '?') || ')' AS before,
    c.coord_status || coalesce(', ' || round(c.border_km, 1) || ' km from border', '') AS after
FROM {{ ref('coord_checks') }} AS c
JOIN {{ ref('parsed_records') }} AS p USING (record_no)
WHERE c.coord_status <> 'inside'
