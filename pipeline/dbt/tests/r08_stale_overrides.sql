-- R08 (warning only): an approval whose from_name is not in this register release does nothing.
-- That is normal when an operator leaves the register, but it can also be a typo in from_name,
-- so dbt reports it without failing the pipeline.
{{ config(severity = 'warn') }}
SELECT o.from_name, o.to_name FROM {{ ref('operator_overrides') }} AS o
WHERE o.from_name NOT IN (SELECT surface_canonical FROM {{ ref('operator_map') }})
