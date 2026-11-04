with d as (
    select * from {{ ref('base_deliveries') }}
),

teams as (
    select * from {{ ref('team_franchises') }}
)

select
    d.match_id,
    d.innings,
    d.is_super_over,
    d.over_no + 1                                                   as over_number,
    d.ball_seq,
    d.legal_ball,
    case
        when d.is_super_over then 'super_over'
        when d.over_no + 1 <= 6 then 'powerplay'
        when d.over_no + 1 <= 15 then 'middle'
        else 'death'
    end                                                             as phase,
    bt.franchise                                                    as batting_team,
    bw.franchise                                                    as bowling_team,
    d.batter,
    d.bowler,
    d.non_striker,
    d.runs_batter,
    d.runs_extras,
    d.runs_total,
    d.extras_wides,
    d.extras_noballs,
    d.extras_byes,
    d.extras_legbyes,
    d.extras_penalty,
    d.is_legal,
    d.extras_wides = 0                                              as is_ball_faced,
    d.runs_batter = 4 and not d.is_non_boundary                     as is_four,
    d.runs_batter = 6 and not d.is_non_boundary                     as is_six,
    d.is_legal and d.runs_total = 0                                 as is_dot,
    d.runs_batter + d.extras_wides + d.extras_noballs               as bowler_runs_conceded,
    d.wicket_count > 0                                              as is_wicket,
    d.wicket_kind,
    d.player_out,
    d.fielders,
    coalesce({{ is_bowler_wicket('d.wicket_kind') }}, false)        as is_bowler_wicket,
    {{ is_dismissal('d.wicket_kind') }}                             as is_dismissal
from d
left join teams bt on bt.team_name = d.batting_team
left join teams bw on bw.team_name = d.bowling_team
