-- R03: plug labels as a ';'-separated German list -> array of normalised plug types.
SELECT
    'R03' AS rule_id, record_no, station_id, point_no, 'fixed' AS action,
    plugs_raw AS before,
    array_to_string(plug_types, ', ') AS after
FROM {{ ref('charging_points') }}
