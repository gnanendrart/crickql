with m as (
    select * from {{ ref('stg_matches') }}
),

innings as (
    select
        match_id,
        innings,
        max(batting_team)                                           as batting_team,
        sum(runs_total)                                             as runs,
        sum(case when is_dismissal then 1 else 0 end)               as wickets,
        sum(case when is_legal then 1 else 0 end)                   as legal_balls
    from {{ ref('stg_deliveries') }}
    where not is_super_over
    group by 1, 2
)

select
    m.*,
    i1.batting_team                                                 as first_innings_team,
    i1.runs                                                         as first_innings_runs,
    i1.wickets                                                      as first_innings_wickets,
    i1.legal_balls                                                  as first_innings_balls,
    i2.batting_team                                                 as second_innings_team,
    i2.runs                                                         as second_innings_runs,
    i2.wickets                                                      as second_innings_wickets,
    i2.legal_balls                                                  as second_innings_balls,
    case
        when m.winner is null or m.decided_by_super_over then null
        when m.winner = i1.batting_team then 'batting first'
        else 'chasing'
    end                                                             as won_by
from m
left join innings i1 on i1.match_id = m.match_id and i1.innings = 1
left join innings i2 on i2.match_id = m.match_id and i2.innings = 2
