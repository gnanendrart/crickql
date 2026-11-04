{# Names, not Cricsheet person IDs: two different players with the same printed name would
   merge here. Not seen in the IPL archive, noted as a known limitation. #}
with appearances as (
    select match_id, season_year, match_date, batter as player, batting_team as team
    from {{ ref('fct_deliveries') }}
    union all
    select match_id, season_year, match_date, non_striker, batting_team
    from {{ ref('fct_deliveries') }}
    union all
    select match_id, season_year, match_date, bowler, bowling_team
    from {{ ref('fct_deliveries') }}
),

latest as (
    select player, team as latest_team,
           row_number() over (partition by player order by match_date desc) as rn
    from appearances
)

select
    a.player,
    min(a.season_year)                                              as first_season,
    max(a.season_year)                                              as last_season,
    count(distinct a.season_year)                                   as seasons_played,
    count(distinct a.match_id)                                      as matches_played,
    count(distinct a.team)                                          as teams_played_for,
    max(l.latest_team)                                              as latest_team
from appearances a
join latest l on l.player = a.player and l.rn = 1
group by 1
