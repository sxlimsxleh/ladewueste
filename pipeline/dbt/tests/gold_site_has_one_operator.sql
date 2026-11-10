-- Sites never mix operators.
SELECT site_id FROM {{ ref('usable_stations') }} GROUP BY site_id HAVING count(DISTINCT operator) > 1
