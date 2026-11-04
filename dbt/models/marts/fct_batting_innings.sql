{# One row per batter per innings, super overs excluded. Includes batters who were run out
   at the non-striker's end without facing a ball. #}
with d as (
    select * from {{ ref('fct_deliveries') }}
    where not is_super_over
),

faced as (
    select
        match_id, innings, batter,
        max(batting_team)                                           as batting_team,
        max(bowling_team)                                           as bowling_team,
        sum(runs_batter)                                            as runs,
        sum(case when is_ball_faced then 1 else 0 end)              as balls_faced,
        sum(case when is_four then 1 else 0 end)                    as fours,
        sum(case when is_six then 1 else 0 end)                     as sixes
    from d
    group by 1, 2, 3
),

outs as (
    select
        match_id, innings, player_out as batter,
        max(batting_team)                                           as batting_team,
        max(bowling_team)                                           as bowling_team,
        max(wicket_kind)                                            as dismissal_kind,
        max(case when is_dismissal then 1 else 0 end)               as is_out
    from d
    where player_out is not null
    group by 1, 2, 3
),

batters as (
    select match_id, innings, batter, batting_team, bowling_team from faced
    union
    select match_id, innings, batter, batting_team, bowling_team from outs
)

select
    b.match_id,
    b.innings,
    b.batter,
    b.batting_team,
    b.bowling_team,
    m.season_year,
    m.match_date,
    m.venue,
    m.is_playoff,
    coalesce(f.runs, 0)                                             as runs,
    coalesce(f.balls_faced, 0)                                      as balls_faced,
    coalesce(f.fours, 0)                                            as fours,
    coalesce(f.sixes, 0)                                            as sixes,
    coalesce(o.is_out, 0) = 1                                       as is_out,
    o.dismissal_kind,
    {{ ratio('coalesce(f.runs, 0)', 'f.balls_faced', 100) }}        as strike_rate
from batters b
join {{ ref('stg_matches') }} m on m.match_id = b.match_id
left join faced f on f.match_id = b.match_id and f.innings = b.innings and f.batter = b.batter
left join outs o on o.match_id = b.match_id and o.innings = b.innings and o.batter = b.batter
