-- R05: implausible power. A point at 0 kW or above the configured max, a station at
-- 0 kW / above max, or a station rated below its own strongest plug. Flagged, not changed.
WITH station_max AS (
    SELECT record_no, max(power_kw) AS max_point_kw, bool_or(power_implausible) AS any_point_implausible
    FROM {{ ref('charging_points') }}
    GROUP BY record_no
)
SELECT
    'R05' AS rule_id, p.record_no, p.station_id, NULL::INTEGER AS point_no, 'flagged' AS action,
    'station ' || p.station_kw || ' kW, strongest plug ' || m.max_point_kw || ' kW' AS before,
    CASE
        WHEN m.any_point_implausible THEN 'point power 0 or > {{ var("max_plausible_point_kw") }} kW'
        WHEN p.station_kw = 0 OR p.station_kw > {{ var('max_plausible_point_kw') }}
            THEN 'station power 0 or > {{ var("max_plausible_point_kw") }} kW'
        ELSE 'station rated below its strongest plug'
    END AS after
FROM {{ ref('parsed_records') }} AS p
JOIN station_max AS m USING (record_no)
WHERE m.any_point_implausible
   OR p.station_kw = 0
   OR p.station_kw > {{ var('max_plausible_point_kw') }}
   OR p.station_kw < m.max_point_kw
