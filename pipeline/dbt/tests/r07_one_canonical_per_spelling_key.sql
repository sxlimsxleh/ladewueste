-- R07: spellings equal up to case/whitespace/punctuation always share one canonical name.
SELECT surface_key, count(DISTINCT surface_canonical) FROM {{ ref('operator_map') }}
GROUP BY surface_key HAVING count(DISTINCT surface_canonical) > 1
