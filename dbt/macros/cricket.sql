{# Shared cricket rules, so every mart counts the same way. #}

{# Wickets credited to the bowler. Run outs, retirements and obstructing the field are not. #}
{% macro is_bowler_wicket(kind) -%}
    ({{ kind }} in ('bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket'))
{%- endmacro %}

{# A dismissal for batting averages. Retired hurt is not out. #}
{% macro is_dismissal(kind) -%}
    ({{ kind }} is not null and {{ kind }} <> 'retired hurt')
{%- endmacro %}

{# Safe ratio rounded to 2 places, works on Postgres and Snowflake. #}
{% macro ratio(num, den, scale=1) -%}
    round(cast({{ num }} * {{ scale }} * 1.0 / nullif({{ den }}, 0) as numeric(12, 4)), 2)
{%- endmacro %}
