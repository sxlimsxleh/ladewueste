-- Every row touched by every cleaning rule, in one table. report.py builds quality_report.json from it.
{%- set rules = ['r01_decimal_commas', 'r02_unpivot_points', 'r03_plug_types', 'r04_kw_list_mismatch',
                 'r05_implausible_power', 'r06_whitespace', 'r07_operator_spelling', 'r08_operator_suggestions',
                 'r09_coordinates', 'r10_placeholder_coords', 'r11_low_precision', 'r12_evse_ids',
                 'r13_duplicates'] %}
{% for r in rules %}
SELECT rule_id, record_no, station_id, point_no, action, before, after FROM {{ ref(r) }}
{% if not loop.last %}UNION ALL{% endif %}
{% endfor %}
