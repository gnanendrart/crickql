TABLE marts.mart_batting_season
  One row per batter per season per team (super overs excluded). For career totals, SUM the counts across seasons and recompute averages and strike rates from the sums; never average the averages.
  - season_year: IPL season as a year.
  - batter: Batter short name, e.g. 'V Kohli', 'DA Warner'.
  - team: Team the batter played for that season (current franchise name).
  - innings: Innings batted.
  - runs: Runs scored.
  - balls_faced: Balls faced (wides excluded).
  - fours: Boundary fours.
  - sixes: Sixes.
  - dismissals: Times out (retired hurt not counted).
  - not_outs: Innings not out.
  - highest_score: Highest score in a single innings that season.
  - fifties: Scores of 50 to 99.
  - hundreds: Scores of 100 or more.
  - ducks: Dismissed for 0.
  - strike_rate: Runs per 100 balls faced.
  - batting_average: Runs per dismissal. Null if never dismissed.

TABLE marts.mart_bowling_phase
  One row per bowler per season per team per phase (powerplay, middle, death; super overs excluded). For a bowler's season or career totals, SUM across phases and recompute economy as runs_conceded * 6 / legal_balls. Overs bowled = legal_balls / 6.
  - season_year: IPL season as a year.
  - bowler: Bowler short name, e.g. 'JJ Bumrah', 'SP Narine'.
  - team: Team the bowler played for (current franchise name).
  - phase: 'powerplay' (overs 1-6), 'middle' (7-15) or 'death' (16-20).
  - matches: Matches in which the bowler bowled in this phase.
  - legal_balls: Legal balls bowled. Divide by 6 for overs.
  - runs_conceded: Runs charged to the bowler (byes and leg byes excluded).
  - wickets: Wickets credited to the bowler (run outs excluded).
  - dot_balls: Legal balls with no runs.
  - fours_conceded: Fours hit off the bowler.
  - sixes_conceded: Sixes hit off the bowler.
  - wides: Wide RUNS conceded, not the number of wides bowled (one wide that runs to the boundary adds 5). For "how many wides did X bowl", use wide_balls.
  - wide_balls: Number of wide deliveries bowled. Use this for "how many wides" or "most wides" questions.
  - noballs: No-ball runs conceded.
  - economy: Runs conceded per over.
  - bowling_average: Runs conceded per wicket.
  - bowling_strike_rate: Legal balls per wicket.
  - dot_ball_pct: Percentage of legal balls that were dots.

TABLE marts.mart_team_season
  One row per team per season. Win/loss record, titles and run rates.
  - season_year: IPL season as a year.
  - team: Franchise (current name).
  - matches: Matches played, including playoffs and no results.
  - wins: Matches won, including super over wins.
  - losses: Matches lost, including super over losses.
  - no_results: Matches with no result.
  - super_over_wins: Tied matches won in a super over.
  - super_over_losses: Tied matches lost in a super over.
  - tosses_won: Tosses won.
  - is_champion: True if the team won that season's final (the IPL title).
  - reached_final: True if the team played in the final.
  - reached_playoffs: True if the team played any playoff match.
  - win_pct: Wins as a percentage of matches with a result.
  - runs_scored: Total runs scored in the season (super overs excluded).
  - runs_conceded: Total runs conceded.
  - run_rate: Runs scored per over.
  - run_rate_conceded: Runs conceded per over.

TABLE marts.fct_matches
  One row per IPL match, 2008 to the latest season. Team names are the current franchise name (Delhi Daredevils appears as Delhi Capitals, Kings XI Punjab as Punjab Kings, Royal Challengers Bangalore as Royal Challengers Bengaluru). Innings totals exclude super overs.
  - match_id: Cricsheet match ID. Primary key.
  - season_year: IPL season as a year, e.g. 2016. Use this for any "in season X" filter.
  - season_label: Cricsheet's original season label, e.g. '2007/08' for the 2008 season. Prefer season_year.
  - match_date: Date the match was played.
  - match_number: League match number within the season. Null for playoff matches.
  - stage: Playoff stage, null for league matches. Values: 'Final', 'Qualifier 1', 'Qualifier 2', 'Eliminator', 'Semi Final' (2008-2010), 'Elimination Final', '3rd Place Play-Off'.
  - is_playoff: True for any knockout match (stage is not null).
  - team1: First team listed (current franchise name). team1 and team2 are in no particular order.
  - team2: Second team listed (current franchise name).
  - team1_name_at_time: team1 as named in that season, e.g. 'Delhi Daredevils'.
  - team2_name_at_time: team2 as named in that season.
  - toss_winner: Team that won the toss (current franchise name).
  - toss_decision: 'bat' or 'field', chosen by the toss winner.
  - venue: Stadium name, cleaned so renamed grounds are one venue (Feroz Shah Kotla is Arun Jaitley Stadium).
  - city: City of the venue, e.g. 'Mumbai', 'Bengaluru'.
  - country: 'India', 'South Africa' (2009 season) or 'UAE' (2014 part-season, 2020, 2021 part-season).
  - result_type: 'normal' (decided in regulation), 'dl' (rain-affected, Duckworth-Lewis), 'tie' (scores level, decided by super over), 'no result' (washed out, no winner).
  - winner: Winning team. For ties this is the super over winner. Null only for no results.
  - loser: Losing team. Null only for no results.
  - win_by_runs: Winning margin in runs when the team batting first won. Null otherwise.
  - win_by_wickets: Winning margin in wickets when the chasing team won. Null otherwise.
  - is_dl_result: True when the result used the Duckworth-Lewis method.
  - decided_by_super_over: True when the match was tied and settled by a super over.
  - target_runs: Runs the chasing side needed. Revised target for D/L matches.
  - target_overs: Overs available for the chase, 20 unless reduced by rain.
  - player_of_match: Player of the match name(s), comma separated.
  - has_super_over: True when the match had at least one super over.
  - has_miscounted_over: True when an umpire bowled a 5- or 7-ball over in this match (recorded by Cricsheet).
  - first_innings_team: Team that batted first.
  - first_innings_runs: Runs scored in the first innings.
  - first_innings_wickets: Wickets lost in the first innings (retired hurt not counted).
  - first_innings_balls: Legal balls faced in the first innings (120 = full 20 overs).
  - second_innings_team: Team that batted second (the chasing team).
  - second_innings_runs: Runs scored in the second innings.
  - second_innings_wickets: Wickets lost in the second innings.
  - second_innings_balls: Legal balls faced in the second innings.
  - won_by: 'batting first' or 'chasing'. Null for no results and super-over ties.

TABLE marts.fct_batting_innings
  One row per batter per innings (super overs excluded). Use for highest scores, fifties, hundreds, ducks, and a player's record against a team or at a venue.
  - match_id: Match. Joins to fct_matches.
  - innings: 1 or 2.
  - batter: Batter short name, e.g. 'V Kohli'.
  - batting_team: Batter's team (current franchise name).
  - bowling_team: Opposition (current franchise name).
  - season_year: IPL season as a year.
  - match_date: Date of the match.
  - venue: Stadium name.
  - is_playoff: True for playoff matches.
  - runs: Runs scored in the innings.
  - balls_faced: Balls faced (wides excluded).
  - fours: Boundary fours hit.
  - sixes: Sixes hit.
  - is_out: True when dismissed. False means not out (an asterisk on a scorecard, e.g. 175*).
  - dismissal_kind: How the batter was out, null if not out.
  - strike_rate: Runs per 100 balls in this innings.

TABLE marts.fct_deliveries
  One row per ball bowled, including wides, no-balls and super overs. The most granular table. Use it for questions the marts cannot answer (head-to-head batter vs bowler, a specific over, partnerships). Filter `not is_super_over` for normal match stats.
  - delivery_id: Text key '<match_id>-<innings>-<over_number>-<ball_seq>'. Primary key.
  - match_id: Match the ball belongs to. Joins to fct_matches.match_id.
  - innings: 1 or 2 for the main innings. 3 and above are super overs.
  - is_super_over: True for super over balls. Exclude these for season and career stats.
  - over_number: Over number, 1 to 20 (1-based).
  - ball_seq: Order of the delivery within the over, counting wides and no-balls.
  - legal_ball: Legal ball number within the over (1-6). Null for wides and no-balls.
  - phase: 'powerplay' (overs 1-6), 'middle' (7-15), 'death' (16-20) or 'super_over'.
  - batting_team: Team batting (current franchise name).
  - bowling_team: Team bowling (current franchise name).
  - batter: Batter on strike, as a short name like 'V Kohli', 'MS Dhoni', 'RG Sharma'.
  - bowler: Bowler, short name like 'JJ Bumrah', 'YS Chahal'.
  - non_striker: Batter at the non-striker's end.
  - runs_batter: Runs credited to the batter off this ball.
  - runs_extras: Extras on this ball (wides + noballs + byes + legbyes + penalty).
  - runs_total: All runs from the ball, runs_batter + runs_extras. Sum this for team totals.
  - extras_wides: Wide runs on this ball (0 if not a wide; can be 2-5 when a wide runs away). To count wides bowled, count rows where extras_wides > 0, do not SUM this column.
  - extras_noballs: No-ball runs on this ball.
  - extras_byes: Byes on this ball.
  - extras_legbyes: Leg byes on this ball.
  - extras_penalty: Penalty runs on this ball (very rare).
  - is_legal: False for wides and no-balls. Count legal balls for overs bowled and economy.
  - is_ball_faced: True when the ball counts as faced by the batter (everything except wides).
  - is_four: True when the batter hit a boundary four (all-run fours excluded).
  - is_six: True when the batter hit a six.
  - is_dot: True for a legal ball with no runs of any kind.
  - bowler_runs_conceded: Runs charged to the bowler (runs_batter + wides + noballs; byes and leg byes are not).
  - is_wicket: True when any player was out on this ball, including run outs.
  - wicket_kind: How the player was out: 'caught', 'bowled', 'run out', 'lbw', 'caught and bowled', 'stumped', 'hit wicket', 'retired hurt', 'retired out', 'obstructing the field'.
  - player_out: Player dismissed. Can be the non-striker (run out), so use this, not batter, to count dismissals.
  - fielders: Fielder(s) involved in the dismissal, comma separated.
  - is_bowler_wicket: True when the wicket counts for the bowler (not run out, retired or obstructing).
  - is_dismissal: True when a player was out for batting-average purposes (retired hurt excluded).
  - season_year: IPL season as a year.
  - match_date: Date of the match.
  - venue: Stadium name.
  - is_playoff: True when the ball was bowled in a playoff match.

TABLE marts.dim_players
  One row per player who batted or bowled. Names are Cricsheet short names ('V Kohli', 'MS Dhoni').
  - player: Player short name. Matches batter, bowler and non_striker in other tables.
  - first_season: First IPL season played.
  - last_season: Most recent IPL season played.
  - seasons_played: Number of seasons with at least one appearance.
  - matches_played: Matches in which the player batted, bowled or was at the non-striker's end.
  - teams_played_for: Number of different franchises.
  - latest_team: Franchise in the player's most recent match.

TABLE marts.dim_venues
  One row per stadium, with batting-first vs chasing record.
  - venue: Stadium name.
  - city: City.
  - country: Country.
  - matches: IPL matches played at the venue.
  - first_season: First season the venue hosted.
  - last_season: Most recent season hosted.
  - avg_first_innings_runs: Average first-innings score in normal (non rain-affected) results.
  - wins_batting_first: Matches won by the team batting first.
  - wins_chasing: Matches won by the chasing team.
  - chasing_win_pct: Percentage of decided matches won by the chasing team.

[11,734 characters, ~2,933 tokens]
