-- R08: a suggested merge changes the canonical operator only if a human approved it.
SELECT operator_clean, surface_canonical, operator_canonical FROM {{ ref('operator_map') }}
WHERE NOT approved AND operator_canonical <> surface_canonical
