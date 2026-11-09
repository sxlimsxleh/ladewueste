-- R12: EVSE-ID cells hold several IDs split by ';', tabs or line breaks, sometimes free text.
-- Valid IDs are kept as a list (fixed); a cell with invalid tokens is flagged.
SELECT
    'R12' AS rule_id, record_no, station_id, point_no,
    CASE WHEN len(evse_invalid_tokens) > 0 THEN 'flagged' ELSE 'fixed' END AS action,
    replace(replace(evse_raw, chr(10), '↵'), chr(9), '⇥') AS before,   -- make line breaks / tabs visible
    '[' || array_to_string(evse_ids, ', ') || ']'
        || CASE WHEN len(evse_invalid_tokens) > 0 THEN ' invalid: ' || array_to_string(evse_invalid_tokens, ' ') ELSE '' END AS after
FROM {{ ref('charging_points') }}
WHERE evse_raw IS NOT NULL
  AND (len(evse_invalid_tokens) > 0 OR evse_raw IS DISTINCT FROM array_to_string(evse_ids, ';'))
