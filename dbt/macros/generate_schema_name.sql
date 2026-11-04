{# Use the custom schema name as-is (staging, marts) instead of dbt's default
   '<target_schema>_<custom>' so the agent always queries `marts.<table>` on both targets. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}
