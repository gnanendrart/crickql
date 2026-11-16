# Gold query review

## q01 (season) verified=False

**Q:** Who took the most wickets in the 2019 season?

```sql
SELECT bowler, SUM(wickets) AS wickets FROM marts.mart_bowling_phase
WHERE season_year = 2019 GROUP BY bowler ORDER BY wickets DESC LIMIT 1
```

Result:

- ['Imran Tahir', 26.0]

Verdict: [ ] correct  [ ] fix: ___

## q02 (season) verified=False

**Q:** How many matches were played in the 2020 season?

```sql
SELECT COUNT(*) FROM marts.fct_matches WHERE season_year = 2020
```

Result:

- [60]

Verdict: [ ] correct  [ ] fix: ___

## q03 (titles) verified=False

**Q:** Who won the IPL final in 2009?

```sql
SELECT team FROM marts.mart_team_season WHERE season_year = 2009 AND is_champion
```

Result:

- ['Deccan Chargers']

Verdict: [ ] correct  [ ] fix: ___

## q04 (career) verified=False

**Q:** Who has hit the most sixes in IPL history?

```sql
SELECT batter, SUM(sixes) FROM marts.mart_batting_season
GROUP BY batter ORDER BY 2 DESC LIMIT 1
```

Result:

- ['CH Gayle', 357.0]

Verdict: [ ] correct  [ ] fix: ___

## q05 (career) verified=False

**Q:** How many IPL hundreds has Virat Kohli scored?

```sql
SELECT SUM(hundreds) FROM marts.mart_batting_season WHERE batter = 'V Kohli'
```

Result:

- [9.0]

Verdict: [ ] correct  [ ] fix: ___

## q06 (career) verified=False

**Q:** Which bowler has the most career IPL wickets?

```sql
SELECT bowler, SUM(wickets) FROM marts.mart_bowling_phase
GROUP BY bowler ORDER BY 2 DESC LIMIT 1
```

Result:

- ['YS Chahal', 233.0]

Verdict: [ ] correct  [ ] fix: ___

## q07 (threshold) verified=False

**Q:** Which batter has the best career batting average with at least 2000 runs?

```sql
SELECT batter, ROUND(SUM(runs) * 1.0 / NULLIF(SUM(dismissals), 0), 2) AS avg
FROM marts.mart_batting_season GROUP BY batter HAVING SUM(runs) >= 2000
ORDER BY avg DESC LIMIT 1
```

Result:

- ['B Sai Sudharsan', 48.37]

Verdict: [ ] correct  [ ] fix: ___

## q08 (threshold) verified=False

**Q:** Which bowler has the best career economy rate, minimum 1000 legal balls?

```sql
SELECT bowler, ROUND(SUM(runs_conceded) * 6.0 / SUM(legal_balls), 2) AS economy
FROM marts.mart_bowling_phase GROUP BY bowler HAVING SUM(legal_balls) >= 1000
ORDER BY economy LIMIT 1
```

Result:

- ['M Muralitharan', 6.68]

Verdict: [ ] correct  [ ] fix: ___

## q09 (phase) verified=False

**Q:** Who has taken the most death-over wickets in IPL history?

```sql
SELECT bowler, SUM(wickets) FROM marts.mart_bowling_phase
WHERE phase = 'death' GROUP BY bowler ORDER BY 2 DESC LIMIT 1
```

Result:

- ['B Kumar', 118.0]

Verdict: [ ] correct  [ ] fix: ___

## q10 (phase) verified=False

**Q:** What was the overall powerplay run rate in the 2025 season?

```sql
SELECT ROUND(SUM(runs_total) * 6.0 / SUM(CASE WHEN is_legal THEN 1 ELSE 0 END), 2)
FROM marts.fct_deliveries
WHERE season_year = 2025 AND phase = 'powerplay'
```

Result:

- [9.61]

Verdict: [ ] correct  [ ] fix: ___

## q11 (head_to_head) verified=False

**Q:** How many times have Kolkata Knight Riders beaten Royal Challengers Bengaluru?

```sql
SELECT COUNT(*) FROM marts.fct_matches
WHERE winner = 'Kolkata Knight Riders' AND loser = 'Royal Challengers Bengaluru'
```

Result:

- [20]

Verdict: [ ] correct  [ ] fix: ___

## q12 (batter_vs_bowler) verified=False

**Q:** How many times has Rashid Khan dismissed MS Dhoni?

```sql
SELECT COUNT(*) FROM marts.fct_deliveries
WHERE bowler = 'Rashid Khan' AND player_out = 'MS Dhoni' AND is_bowler_wicket
  AND NOT is_super_over
```

Result:

- [1]

Verdict: [ ] correct  [ ] fix: ___

## q13 (venue) verified=False

**Q:** Which venue has hosted the most IPL matches?

```sql
SELECT venue, matches FROM marts.dim_venues ORDER BY matches DESC LIMIT 1
```

Result:

- ['Wankhede Stadium', 132]

Verdict: [ ] correct  [ ] fix: ___

## q14 (venue) verified=False

**Q:** How many IPL matches were played in South Africa?

```sql
SELECT COUNT(*) FROM marts.fct_matches WHERE country = 'South Africa'
```

Result:

- [57]

Verdict: [ ] correct  [ ] fix: ___

## q15 (super_over) verified=False

**Q:** How many IPL matches have been decided by a super over?

```sql
SELECT COUNT(*) FROM marts.fct_matches WHERE decided_by_super_over
```

Result:

- [16]

Verdict: [ ] correct  [ ] fix: ___

## q16 (super_over) verified=False

**Q:** Which team has won the most super overs?

```sql
SELECT team, SUM(super_over_wins) AS wins FROM marts.mart_team_season
GROUP BY team ORDER BY wins DESC LIMIT 1
```

Result:

- ['Delhi Capitals', 4.0]

Verdict: [ ] correct  [ ] fix: ___

## q17 (innings) verified=False

**Q:** What is the highest team total in an IPL innings?

```sql
SELECT MAX(GREATEST(first_innings_runs, second_innings_runs)) FROM marts.fct_matches
```

Result:

- [287]

Verdict: [ ] correct  [ ] fix: ___

## q18 (innings) verified=False

**Q:** What is the lowest completed first-innings total in the IPL (all out or 20 overs, no rain)?

```sql
SELECT MIN(first_innings_runs) FROM marts.fct_matches
WHERE result_type IN ('normal', 'tie')
  AND (first_innings_wickets = 10 OR first_innings_balls = 120)
```

Result:

- [67]

Verdict: [ ] correct  [ ] fix: ___

## q19 (innings) verified=False

**Q:** Who has the most fifties (50 to 99) in IPL history?

```sql
SELECT batter, SUM(fifties) FROM marts.mart_batting_season
GROUP BY batter ORDER BY 2 DESC LIMIT 1
```

Result:

- ['V Kohli', 68.0]

Verdict: [ ] correct  [ ] fix: ___

## q20 (innings) verified=False

**Q:** How many ducks has Rohit Sharma made in the IPL?

```sql
SELECT SUM(ducks) FROM marts.mart_batting_season WHERE batter = 'RG Sharma'
```

Result:

- [19.0]

Verdict: [ ] correct  [ ] fix: ___

## q21 (team) verified=False

**Q:** Which team had the best win percentage in the 2008 season?

```sql
SELECT team, win_pct FROM marts.mart_team_season
WHERE season_year = 2008 ORDER BY win_pct DESC LIMIT 1
```

Result:

- ['Rajasthan Royals', 81.25]

Verdict: [ ] correct  [ ] fix: ___

## q22 (team) verified=False

**Q:** How many finals have Chennai Super Kings played?

```sql
SELECT COUNT(*) FROM marts.mart_team_season
WHERE team = 'Chennai Super Kings' AND reached_final
```

Result:

- [10]

Verdict: [ ] correct  [ ] fix: ___

## q23 (toss) verified=False

**Q:** In how many matches did the toss winner choose to field first?

```sql
SELECT COUNT(*) FROM marts.fct_matches WHERE toss_decision = 'field'
```

Result:

- [825]

Verdict: [ ] correct  [ ] fix: ___

## q24 (results) verified=False

**Q:** How many matches were affected by rain and decided by Duckworth-Lewis?

```sql
SELECT COUNT(*) FROM marts.fct_matches WHERE is_dl_result
```

Result:

- [23]

Verdict: [ ] correct  [ ] fix: ___

## q25 (results) verified=False

**Q:** What is the biggest winning margin by runs in IPL history, and who won?

```sql
SELECT winner, loser, win_by_runs, season_year FROM marts.fct_matches
WHERE win_by_runs = (SELECT MAX(win_by_runs) FROM marts.fct_matches)
```

Result:

- ['Mumbai Indians', 'Delhi Capitals', 146, 2017]

Verdict: [ ] correct  [ ] fix: ___

## q26 (dismissals) verified=False

**Q:** How many run outs have there been in IPL history, super overs excluded?

```sql
SELECT COUNT(*) FROM marts.fct_deliveries
WHERE wicket_kind = 'run out' AND NOT is_super_over
```

Result:

- [1185]

Verdict: [ ] correct  [ ] fix: ___

## q27 (extras) verified=False

**Q:** Which team bowled the most wides in the 2022 season?

```sql
SELECT bowling_team, SUM(extras_wides) FROM marts.fct_deliveries
WHERE season_year = 2022 AND NOT is_super_over
GROUP BY bowling_team ORDER BY 2 DESC LIMIT 1
```

Result:

- ['Rajasthan Royals', 129]

Verdict: [ ] correct  [ ] fix: ___

## q28 (players) verified=False

**Q:** Which player has played in the most IPL seasons?

```sql
SELECT player, seasons_played FROM marts.dim_players
WHERE seasons_played = (SELECT MAX(seasons_played) FROM marts.dim_players)
```

Result:

- ['MK Pandey', 19]
- ['RG Sharma', 19]
- ['V Kohli', 19]

Verdict: [ ] correct  [ ] fix: ___

## q29 (playoffs) verified=False

**Q:** Who has scored the most runs in IPL playoff matches?

```sql
SELECT batter, SUM(runs) FROM marts.fct_batting_innings
WHERE is_playoff GROUP BY batter ORDER BY 2 DESC LIMIT 1
```

Result:

- ['SK Raina', 714.0]

Verdict: [ ] correct  [ ] fix: ___

## q30 (season) verified=False

**Q:** Who won the orange cap (most runs) in each season from 2020 to 2024?

```sql
SELECT season_year, batter, runs FROM (
  SELECT season_year, batter, SUM(runs) AS runs,
         RANK() OVER (PARTITION BY season_year ORDER BY SUM(runs) DESC) AS rk
  FROM marts.mart_batting_season WHERE season_year BETWEEN 2020 AND 2024
  GROUP BY season_year, batter) t
WHERE rk = 1
```

Result:

- [2020, 'KL Rahul', 670.0]
- [2021, 'RD Gaikwad', 635.0]
- [2022, 'JC Buttler', 863.0]
- [2023, 'Shubman Gill', 890.0]
- [2024, 'V Kohli', 741.0]

Verdict: [ ] correct  [ ] fix: ___

