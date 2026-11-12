{# One row per match with the raw.matches column contract, on either target. #}
{% if target.type == 'snowflake' %}

with src as (
    select
        -- file name is <match_id>.json (S3) or <match_id>.json.gz (internal stage, gzipped by PUT)
        cast(split_part(split_part(file_name, '/', -1), '.', 1) as bigint) as match_id,
        file_name,
        doc
    from {{ source('raw', 'matches_json') }}
),

innings_flags as (
    select
        s.match_id,
        max(i.value:target:runs::int)                                   as target_runs,
        max(i.value:target:overs::number(4, 1))                         as target_overs,
        max(iff(i.value:miscounted_overs is not null, 1, 0))            as has_miscounted
    from src s, lateral flatten(input => s.doc:innings) i
    group by 1
)

select
    s.match_id,
    s.doc:info:season::string                                           as season_raw,
    year(s.doc:info:dates[0]::date)                                     as season_year,
    s.doc:info:dates[0]::date                                           as match_date,
    s.doc:info:event:name::string                                       as event_name,
    s.doc:info:event:match_number::int                                  as match_number,
    s.doc:info:event:stage::string                                      as stage,
    s.doc:info:teams[0]::string                                         as team1,
    s.doc:info:teams[1]::string                                         as team2,
    s.doc:info:toss:winner::string                                      as toss_winner,
    s.doc:info:toss:decision::string                                    as toss_decision,
    s.doc:info:venue::string                                            as venue,
    s.doc:info:city::string                                             as city,
    case
        when s.doc:info:outcome:result::string = 'no result' then 'no result'
        when s.doc:info:outcome:result::string = 'tie' then 'tie'
        when s.doc:info:outcome:method is not null then 'dl'
        else 'normal'
    end                                                                 as result_type,
    coalesce(s.doc:info:outcome:winner::string,
             s.doc:info:outcome:eliminator::string)                     as winner,
    s.doc:info:outcome:by:runs::int                                     as win_by_runs,
    s.doc:info:outcome:by:wickets::int                                  as win_by_wickets,
    s.doc:info:outcome:method::string                                   as method,
    s.doc:info:outcome:eliminator is not null                           as decided_by_super_over,
    f.target_runs,
    f.target_overs,
    array_to_string(s.doc:info:player_of_match, ', ')                   as player_of_match,
    s.doc:info:overs::int                                               as scheduled_overs,
    coalesce(s.doc:info:balls_per_over::int, 6)                         as balls_per_over,
    array_size(s.doc:innings)                                           as innings_count,
    array_size(s.doc:innings) > 2                                       as has_super_over,
    f.has_miscounted = 1                                                as has_miscounted_over,
    s.doc:meta:data_version::string                                     as data_version,
    split_part(s.file_name, '/', -1)                                    as source_file
from src s
left join innings_flags f using (match_id)

{% else %}

select * from {{ source('raw', 'matches') }}

{% endif %}
