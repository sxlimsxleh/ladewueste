-- R09/R10/R11/R13: nothing usable for coverage is outside Germany, a placeholder,
-- whole-degree precision or a duplicate.
SELECT station_id, coord_status, is_placeholder_coord, coord_decimals, duplicate_of
FROM {{ ref('stations') }}
WHERE usable_for_coverage
  AND (coord_status NOT IN ('inside', 'swapped', 'border_tolerance')
       OR is_placeholder_coord OR coord_decimals = 0 OR duplicate_of IS NOT NULL)
