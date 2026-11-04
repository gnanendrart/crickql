with bi as (
    select * from {{ ref('fct_batting_innings') }}
)

select
    season_year,
    batter,
    batting_team                                                    as team,
    count(*)                                                        as innings,
    sum(runs)                                                       as runs,
    sum(balls_faced)                                                as balls_faced,
    sum(fours)                                                      as fours,
    sum(sixes)                                                      as sixes,
    sum(case when is_out then 1 else 0 end)                         as dismissals,
    sum(case when is_out then 0 else 1 end)                         as not_outs,
    max(runs)                                                       as highest_score,
    sum(case when runs between 50 and 99 then 1 else 0 end)         as fifties,
    sum(case when runs >= 100 then 1 else 0 end)                    as hundreds,
    sum(case when runs = 0 and is_out then 1 else 0 end)            as ducks,
    {{ ratio('sum(runs)', 'sum(balls_faced)', 100) }}               as strike_rate,
    {{ ratio('sum(runs)', 'sum(case when is_out then 1 else 0 end)') }} as batting_average
from bi
group by 1, 2, 3
