with m as (
    select * from {{ ref('fct_matches') }}
),

team_matches as (
    select season_year, team1 as team, match_id from m
    union all
    select season_year, team2 as team, match_id from m
),

runs as (
    select season_year, batting_team as team,
           sum(runs_total) as runs_scored, sum(case when is_legal then 1 else 0 end) as balls_faced
    from {{ ref('fct_deliveries') }} where not is_super_over group by 1, 2
),

conceded as (
    select season_year, bowling_team as team,
           sum(runs_total) as runs_conceded, sum(case when is_legal then 1 else 0 end) as balls_bowled
    from {{ ref('fct_deliveries') }} where not is_super_over group by 1, 2
),

record as (
    select
        tm.season_year,
        tm.team,
        count(*)                                                                as matches,
        sum(case when m.winner = tm.team then 1 else 0 end)                     as wins,
        sum(case when m.loser = tm.team then 1 else 0 end)                      as losses,
        sum(case when m.result_type = 'no result' then 1 else 0 end)            as no_results,
        sum(case when m.decided_by_super_over and m.winner = tm.team then 1 else 0 end)
                                                                                as super_over_wins,
        sum(case when m.decided_by_super_over and m.loser = tm.team then 1 else 0 end)
                                                                                as super_over_losses,
        sum(case when m.toss_winner = tm.team then 1 else 0 end)                as tosses_won,
        max(case when m.stage = 'Final' and m.winner = tm.team then 1 else 0 end) = 1
                                                                                as is_champion,
        max(case when m.stage = 'Final' then 1 else 0 end) = 1                  as reached_final,
        max(case when m.is_playoff then 1 else 0 end) = 1                       as reached_playoffs
    from team_matches tm
    join m on m.match_id = tm.match_id
    group by 1, 2
)

select
    r.*,
    {{ ratio('r.wins', 'r.matches - r.no_results', 100) }}          as win_pct,
    ru.runs_scored,
    co.runs_conceded,
    {{ ratio('ru.runs_scored', 'ru.balls_faced', 6) }}              as run_rate,
    {{ ratio('co.runs_conceded', 'co.balls_bowled', 6) }}           as run_rate_conceded
from record r
left join runs ru on ru.season_year = r.season_year and ru.team = r.team
left join conceded co on co.season_year = r.season_year and co.team = r.team
