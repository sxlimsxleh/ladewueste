-- R13: records sharing a valid EVSE-ID (which must be unique) are duplicates. The lowest
-- station_id in the group stays primary; the others get duplicate_of and are flagged, not deleted.
-- Groups are connected components: A shares an ID with B, B with C -> A, B, C are one group.
WITH RECURSIVE pairs AS (
    SELECT DISTINCT a.station_id AS id, b.station_id AS other
    FROM (SELECT station_id, unnest(evse_ids) AS evse FROM {{ ref('charging_points') }}) AS a
    JOIN (SELECT station_id, unnest(evse_ids) AS evse FROM {{ ref('charging_points') }}) AS b
      ON a.evse = b.evse AND a.station_id <> b.station_id
),
reach (id, other) AS (
    SELECT id, other FROM pairs
    UNION
    SELECT r.id, p.other FROM reach AS r JOIN pairs AS p ON p.id = r.other WHERE p.other <> r.id
),
groups AS (
    SELECT id AS station_id, least(min(other::BIGINT), id::BIGINT)::VARCHAR AS primary_id
    FROM reach
    GROUP BY id
)
SELECT
    'R13' AS rule_id, p.record_no, g.station_id, NULL::INTEGER AS point_no, 'flagged' AS action,
    'station ' || g.station_id AS before,
    'duplicate_of ' || g.primary_id AS after,
    g.primary_id AS duplicate_of
FROM groups AS g
JOIN {{ ref('parsed_records') }} AS p USING (station_id)
WHERE g.station_id <> g.primary_id
