-- R08: an approved merge must point to an operator that exists. Catches typos in to_name, which
-- would otherwise merge an operator into a name nobody has.
SELECT o.from_name, o.to_name FROM {{ ref('operator_overrides') }} AS o
WHERE o.from_name IN (SELECT surface_canonical FROM {{ ref('operator_map') }})
  AND o.to_name NOT IN (SELECT surface_canonical FROM {{ ref('operator_map') }})
