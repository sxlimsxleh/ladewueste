-- R04: the number of kW values differs from the number of plugs, so plug and power
-- cannot be paired. The point keeps max(kW) as its power and is flagged.
SELECT
    'R04' AS rule_id, record_no, station_id, point_no, 'flagged' AS action,
    plugs_raw || '  →  ' || kw_raw AS before,
    len(plug_labels) || ' plugs, ' || len(kw_values) || ' kW values; power_kw = ' || power_kw AS after
FROM {{ ref('charging_points') }}
WHERE kw_list_mismatch
