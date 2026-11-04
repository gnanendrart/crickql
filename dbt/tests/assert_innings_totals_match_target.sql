-- Silent-failure guard: for every match decided normally or by a tie, the first innings total
-- built from ball-level rows must equal the official target minus one. If the parse, the load
-- or a staging join drops or duplicates a single ball, this test fails.
select match_id, first_innings_runs, target_runs
from {{ ref('fct_matches') }}
where result_type in ('normal', 'tie')
  and target_runs is not null
  and first_innings_runs + 1 <> target_runs
