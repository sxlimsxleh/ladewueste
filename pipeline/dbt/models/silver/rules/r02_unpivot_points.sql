-- R02: up to N charging points stored side by side in wide column groups -> one row each.
SELECT
    'R02' AS rule_id, record_no, station_id, NULL::INTEGER AS point_no, 'fixed' AS action,
    '{{ var("n_point_groups") }} column groups, ' || count(*) || ' filled' AS before,
    count(*) || ' charging_points rows' AS after
FROM {{ ref('charging_points') }}
GROUP BY record_no, station_id
