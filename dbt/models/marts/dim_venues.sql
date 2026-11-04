with m as (
    select * from {{ ref('fct_matches') }}
)

select
    venue,
    max(city)                                                                   as city,
    max(country)                                                                as country,
    count(*)                                                                    as matches,
    min(season_year)                                                            as first_season,
    max(season_year)                                                            as last_season,
    {{ ratio('sum(case when result_type = \'normal\' then first_innings_runs end)',
             'sum(case when result_type = \'normal\' then 1 end)') }}           as avg_first_innings_runs,
    sum(case when won_by = 'batting first' then 1 else 0 end)                   as wins_batting_first,
    sum(case when won_by = 'chasing' then 1 else 0 end)                         as wins_chasing,
    {{ ratio('sum(case when won_by = \'chasing\' then 1 else 0 end)',
             'sum(case when won_by is not null then 1 else 0 end)', 100) }}     as chasing_win_pct
from m
group by 1
