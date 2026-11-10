-- One row per (res, cell).
SELECT res, cell, count(*) FROM {{ ref('hexes') }} GROUP BY res, cell HAVING count(*) > 1
