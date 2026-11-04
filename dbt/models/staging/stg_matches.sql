with m as (
    select * from {{ ref('base_matches') }}
),

teams as (
    select * from {{ ref('team_franchises') }}
),

venues as (
    select * from {{ ref('venue_aliases') }}
)

select
    m.match_id,
    m.season_year,
    m.season_raw                                    as season_label,
    m.match_date,
    m.match_number,
    m.stage,
    m.stage is not null                             as is_playoff,
    t1.franchise                                    as team1,
    t2.franchise                                    as team2,
    m.team1                                         as team1_name_at_time,
    m.team2                                         as team2_name_at_time,
    tw.franchise                                    as toss_winner,
    m.toss_decision,
    coalesce(v.venue, m.venue)                      as venue,
    coalesce(v.city, m.city)                        as city,
    v.country,
    m.result_type,
    w.franchise                                     as winner,
    case
        when w.franchise is null then null
        when w.franchise = t1.franchise then t2.franchise
        else t1.franchise
    end                                             as loser,
    m.win_by_runs,
    m.win_by_wickets,
    m.method is not null                            as is_dl_result,
    m.decided_by_super_over,
    m.target_runs,
    m.target_overs,
    m.player_of_match,
    m.has_super_over,
    m.has_miscounted_over
from m
left join teams t1 on t1.team_name = m.team1
left join teams t2 on t2.team_name = m.team2
left join teams tw on tw.team_name = m.toss_winner
left join teams w on w.team_name = m.winner
left join venues v on v.venue_raw = m.venue
