-- R06: no cleaned text field has non-breaking spaces, edge spaces or double spaces.
{%- set fields = ['operator', 'display_name', 'street', 'house_no', 'town', 'district', 'state'] %}
SELECT station_id FROM {{ ref('stations') }}
WHERE {% for f in fields %}({{ f }} <> trim({{ f }}) OR contains({{ f }}, chr(160)) OR contains({{ f }}, '  ')){% if not loop.last %} OR {% endif %}{% endfor %}
