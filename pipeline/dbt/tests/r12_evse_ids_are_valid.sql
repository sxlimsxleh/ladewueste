-- R12: every kept EVSE-ID matches the ISO 15118 pattern.
SELECT record_no, point_no, evse FROM (
    SELECT record_no, point_no, unnest(evse_ids) AS evse FROM {{ ref('charging_points') }}
) WHERE NOT regexp_full_match(evse, {{ evse_pattern() }})
