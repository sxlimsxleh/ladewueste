-- R08: every approved merge names operators that exist (catches typos in the seed).
SELECT o.from_name, o.to_name FROM {{ ref('operator_overrides') }} AS o
WHERE o.from_name NOT IN (SELECT surface_canonical FROM {{ ref('operator_map') }})
   OR o.to_name NOT IN (SELECT surface_canonical FROM {{ ref('operator_map') }})
