{# One row per delivery with the raw.deliveries column contract, on either target. #}
{% if target.type == 'snowflake' %}

with flat as (
    select
        cast(replace(split_part(m.file_name, '/', -1), '.json', '') as bigint) as match_id,
        i.index + 1                                                      as innings,
        o.value:over::int                                                as over_no,
        d.index + 1                                                      as ball_seq,
        d.value:actual_delivery::string                                  as actual_delivery,
        i.value:team::string                                             as batting_team,
        iff(i.value:team::string = m.doc:info:teams[0]::string,
            m.doc:info:teams[1]::string, m.doc:info:teams[0]::string)    as bowling_team,
        coalesce(i.value:super_over::boolean, false)                     as is_super_over,
        d.value:batter::string                                           as batter,
        d.value:bowler::string                                           as bowler,
        d.value:non_striker::string                                      as non_striker,
        d.value:runs:batter::int                                         as runs_batter,
        d.value:runs:extras::int                                         as runs_extras,
        d.value:runs:total::int                                          as runs_total,
        coalesce(d.value:runs:non_boundary::boolean, false)              as is_non_boundary,
        coalesce(d.value:extras:wides::int, 0)                           as extras_wides,
        coalesce(d.value:extras:noballs::int, 0)                         as extras_noballs,
        coalesce(d.value:extras:byes::int, 0)                            as extras_byes,
        coalesce(d.value:extras:legbyes::int, 0)                         as extras_legbyes,
        coalesce(d.value:extras:penalty::int, 0)                         as extras_penalty,
        coalesce(array_size(d.value:wickets), 0)                         as wicket_count,
        d.value:wickets[0]:kind::string                                  as wicket_kind,
        d.value:wickets[0]:player_out::string                            as player_out,
        -- simplification: first fielder only (Postgres path keeps all, comma separated)
        d.value:wickets[0]:fielders[0]:name::string                      as fielders
    from {{ source('raw', 'matches_json') }} m,
        lateral flatten(input => m.doc:innings) i,
        lateral flatten(input => i.value:overs) o,
        lateral flatten(input => o.value:deliveries) d
)

select
    match_id, innings, over_no, ball_seq,
    case when extras_wides = 0 and extras_noballs = 0 then
        sum(iff(extras_wides = 0 and extras_noballs = 0, 1, 0)) over (
            partition by match_id, innings, over_no order by ball_seq
            rows between unbounded preceding and current row)
    end                                                                  as legal_ball,
    actual_delivery, batting_team, bowling_team, is_super_over, batter, bowler, non_striker,
    runs_batter, runs_extras, runs_total, is_non_boundary,
    extras_wides, extras_noballs, extras_byes, extras_legbyes, extras_penalty,
    extras_wides = 0 and extras_noballs = 0                              as is_legal,
    wicket_count, wicket_kind, player_out, fielders
from flat

{% else %}

select * from {{ source('raw', 'deliveries') }}

{% endif %}
