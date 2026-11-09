{#- Cleaning logic lives in macros so the rule model that REPORTS a fix and the
    silver model that APPLIES it use exactly the same expression. -#}

{#- Non-breaking spaces -> spaces, collapse runs of whitespace, trim. -#}
{% macro clean_text(column) -%}
    nullif(trim(regexp_replace(replace({{ column }}, chr(160), ' '), '\s+', ' ', 'g')), '')
{%- endmacro %}

{#- German decimal '3,7' -> 3.7. try_cast: unparsable text becomes NULL (and is caught by tests). -#}
{% macro german_decimal(column) -%}
    try_cast(replace(trim({{ column }}), ',', '.') AS DOUBLE)
{%- endmacro %}

{#- '22; 22' -> ['22', '22'] (one value per plug); empty pieces removed. -#}
{% macro split_list(column) -%}
    list_filter(list_transform(string_split({{ column }}, ';'), lambda x: trim(x)), lambda x: x <> '')
{%- endmacro %}

{#- Number of decimals in a German-formatted coordinate ('48,4423' -> 4, '48' -> 0). -#}
{% macro decimals(column) -%}
    CASE WHEN contains({{ column }}, ',') THEN length(split_part(trim({{ column }}), ',', 2)) ELSE 0 END
{%- endmacro %}

{#- ISO 15118 / eMI3 EVSE-ID: country (2) + operator (3) + 'E' + up to 31 chars, '*' optional. -#}
{% macro evse_pattern() -%}
    '^[A-Z]{2}\*?[A-Z0-9]{3}\*?E[A-Z0-9*]{1,31}$'
{%- endmacro %}
