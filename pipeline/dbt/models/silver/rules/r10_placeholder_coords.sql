-- R10: one coordinate used by stations in many different towns is a placeholder, not a location.
WITH placeholders AS (
    SELECT lat_parsed, lon_parsed, count(DISTINCT town) AS n_towns
    FROM {{ ref('parsed_records') }}
    WHERE lat_parsed IS NOT NULL AND lon_parsed IS NOT NULL
    GROUP BY lat_parsed, lon_parsed
    HAVING count(DISTINCT town) >= {{ var('placeholder_min_towns') }}
)
SELECT
    'R10' AS rule_id, p.record_no, p.station_id, NULL::INTEGER AS point_no, 'flagged' AS action,
    p.lat_parsed || ', ' || p.lon_parsed || ' (' || p.town || ')' AS before,
    'placeholder: same point used in ' || ph.n_towns || ' towns' AS after
FROM {{ ref('parsed_records') }} AS p
JOIN placeholders AS ph USING (lat_parsed, lon_parsed)
