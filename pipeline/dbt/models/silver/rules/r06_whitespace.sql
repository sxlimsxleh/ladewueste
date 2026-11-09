-- R06: stray whitespace and non-breaking spaces (U+00A0) in text fields. One row per changed field.
{%- set fields = ['operator', 'display_name', 'street', 'house_no', 'address_extra', 'postcode', 'town', 'district', 'state'] %}
{% for f in fields %}
SELECT
    'R06' AS rule_id, record_no, station_id, NULL::INTEGER AS point_no, 'fixed' AS action,
    '{{ f }}: ' || replace({{ f }}_raw, chr(160), '⍽') AS before,   -- ⍽ makes the invisible NBSP visible
    '{{ f }}: ' || coalesce({{ clean_text(f ~ '_raw') }}, '(empty)') AS after
FROM {{ ref('stg_records') }}
WHERE {{ f }}_raw IS DISTINCT FROM {{ clean_text(f ~ '_raw') }}
{% if not loop.last %}UNION ALL{% endif %}
{% endfor %}
