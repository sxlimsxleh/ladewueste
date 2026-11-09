-- R13: duplicate_of always names an existing record that is itself not a duplicate.
SELECT d.station_id, d.duplicate_of
FROM {{ ref('stations') }} AS d
LEFT JOIN {{ ref('stations') }} AS p ON p.station_id = d.duplicate_of
WHERE d.duplicate_of IS NOT NULL AND (p.station_id IS NULL OR p.duplicate_of IS NOT NULL)
