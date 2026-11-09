-- R02: (record_no, point_no) identifies a charging point.
SELECT record_no, point_no, count(*) FROM {{ ref('charging_points') }}
GROUP BY record_no, point_no HAVING count(*) > 1
