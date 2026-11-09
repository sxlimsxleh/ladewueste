-- R02: the unpivot produces exactly as many points as the register declares per record.
SELECT p.record_no, p.n_points AS declared, count(c.point_no) AS unpivoted
FROM {{ ref('parsed_records') }} AS p
LEFT JOIN {{ ref('charging_points') }} AS c USING (record_no)
GROUP BY p.record_no, p.n_points
HAVING p.n_points IS DISTINCT FROM count(c.point_no)
