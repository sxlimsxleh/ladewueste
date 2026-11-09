{#- Use the custom schema name as-is (silver, staging, ref) instead of dbt's default
    "<target_schema>_<custom>" prefixing, so tables are simply silver.stations etc. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name is not none else target.schema }}
{%- endmacro %}
