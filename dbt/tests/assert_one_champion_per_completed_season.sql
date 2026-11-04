-- Every season with a final has exactly one champion.
select season_year, sum(case when is_champion then 1 else 0 end) as champions
from {{ ref('mart_team_season') }}
group by season_year
having max(case when reached_final then 1 else 0 end) = 1
   and sum(case when is_champion then 1 else 0 end) <> 1
