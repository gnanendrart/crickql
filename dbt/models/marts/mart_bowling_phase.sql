with d as (
    select * from {{ ref('fct_deliveries') }}
    where not is_super_over
)

select
    season_year,
    bowler,
    bowling_team                                                    as team,
    phase,
    count(distinct match_id)                                        as matches,
    sum(case when is_legal then 1 else 0 end)                       as legal_balls,
    sum(bowler_runs_conceded)                                       as runs_conceded,
    sum(case when is_bowler_wicket then 1 else 0 end)               as wickets,
    sum(case when is_dot then 1 else 0 end)                         as dot_balls,
    sum(case when is_four then 1 else 0 end)                        as fours_conceded,
    sum(case when is_six then 1 else 0 end)                         as sixes_conceded,
    sum(extras_wides)                                               as wides,
    sum(case when extras_wides > 0 then 1 else 0 end)               as wide_balls,
    sum(extras_noballs)                                             as noballs,
    {{ ratio('sum(bowler_runs_conceded)', 'sum(case when is_legal then 1 else 0 end)', 6) }}
                                                                    as economy,
    {{ ratio('sum(bowler_runs_conceded)', 'sum(case when is_bowler_wicket then 1 else 0 end)') }}
                                                                    as bowling_average,
    {{ ratio('sum(case when is_legal then 1 else 0 end)',
             'sum(case when is_bowler_wicket then 1 else 0 end)') }} as bowling_strike_rate,
    {{ ratio('sum(case when is_dot then 1 else 0 end)', 'sum(case when is_legal then 1 else 0 end)', 100) }}
                                                                    as dot_ball_pct
from d
group by 1, 2, 3, 4
