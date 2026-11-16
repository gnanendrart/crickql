# Gold query review

## h01 (unanswerable) verified=False

**Q:** Which team did Sharma captain to a title win

Expect: not answerable (no gold SQL)

## h02 (ambiguous) verified=False

**Q:** How many runs did the Royals score in the final?

```sql
SELECT
season_year,
CASE WHEN first_innings_team = 'Rajasthan Royals'
     THEN first_innings_runs ELSE second_innings_runs END AS runs,
CASE WHEN first_innings_team = 'Rajasthan Royals'
     THEN first_innings_wickets ELSE second_innings_wickets END AS wickets
FROM marts.fct_matches
WHERE stage = 'Final'
AND 'Rajasthan Royals' IN (team1, team2)
ORDER BY season_year
```

Result:

- [2008, 164, 7]
- [2022, 130, 9]

Verdict: [ ] correct  [ ] fix: ___

## h03 (nickname) verified=False

**Q:** How many centuries has the Universe Boss scored in IPL history?

```sql
SELECT 
batter,
SUM(hundreds) AS total_centuries
FROM marts.mart_batting_season
WHERE batter = 'CH Gayle'
GROUP BY batter;
```

Result:

- ['CH Gayle', 6.0]

Verdict: [ ] correct  [ ] fix: ___

## h04 (comparison) verified=False

**Q:** Who has scored more career runs in the IPL, Virat Kohli or Rohit Sharma?

```sql
SELECT 
batter,
SUM(runs) AS career_runs
FROM marts.mart_batting_season
WHERE batter IN ('V Kohli', 'RG Sharma')
GROUP BY batter
ORDER BY career_runs DESC;
```

Result:

- ['V Kohli', 9336.0]
- ['RG Sharma', 7329.0]

Verdict: [ ] correct  [ ] fix: ___

## h05 (comparison) verified=False

**Q:** Between Mumbai Indians and Chennai Super Kings, which team has a better head-to-head win record?

```sql
SELECT 
winner,
COUNT(*) AS wins
FROM marts.fct_matches
WHERE ((team1 = 'Mumbai Indians' AND team2 = 'Chennai Super Kings')
OR (team1 = 'Chennai Super Kings' AND team2 = 'Mumbai Indians'))
AND winner IS NOT NULL
GROUP BY winner
ORDER BY wins DESC;
```

Result:

- ['Mumbai Indians', 21]
- ['Chennai Super Kings', 20]

Verdict: [ ] correct  [ ] fix: ___

## h06 (unanswerable) verified=False

**Q:** • How many wickets did Don Bradman take in his debut IPL season?

Expect: not answerable (no gold SQL)

## h07 (unanswerable) verified=False

**Q:** Who will win the Orange Cap in the 2030 IPL season?

Expect: not answerable (no gold SQL)

## h08 (multi_step) verified=False

**Q:** Which player won the Orange Cap in the same season that Sunrisers Hyderabad won their first IPL title, and how many runs did he score?

```sql
WITH srh_first_title AS (
SELECT MIN(season_year) AS title_year
FROM marts.mart_team_season
WHERE team = 'Sunrisers Hyderabad'
  AND is_champion = TRUE)
SELECT 
b.batter,
SUM(b.runs) AS total_runs
FROM marts.mart_batting_season b
JOIN srh_first_title s ON b.season_year = s.title_year
GROUP BY b.batter
ORDER BY total_runs DESC
LIMIT 1;
```

Result:

- ['V Kohli', 973.0]

Verdict: [ ] correct  [ ] fix: ___

## h09 (multi_step) verified=False

**Q:** Which franchise has hit the most sixes in a single IPL season, and which player hit the most sixes during that campaign?

```sql
WITH top_team_season AS (
SELECT 
    team,
    season_year,
    SUM(sixes) AS team_sixes
FROM marts.mart_batting_season
GROUP BY team, season_year
ORDER BY team_sixes DESC
LIMIT 1)
SELECT 
t.team AS franchise,
t.season_year,
t.team_sixes,
b.batter AS top_six_hitter,
b.sixes AS player_sixes
FROM top_team_season t
JOIN marts.mart_batting_season b 
ON b.team = t.team 
AND b.season_year = t.season_year
ORDER BY b.sixes DESC
LIMIT 1;
```

Result:

- ['Rajasthan Royals', 2026, 181.0, 'V Suryavanshi', 72.0]

Verdict: [ ] correct  [ ] fix: ___

## h10 (multi_step) verified=False

**Q:** Which bowler won the Purple Cap in the season that Gujarat Titans won their debut IPL title, and which team did he play for?

```sql
WITH gt_debut_title AS (
SELECT MIN(season_year) AS title_year
FROM marts.mart_team_season
WHERE team = 'Gujarat Titans'
  AND is_champion = TRUE)
SELECT 
p.bowler,
p.team,
SUM(p.wickets) AS season_wickets
FROM marts.mart_bowling_phase p
JOIN gt_debut_title g ON p.season_year = g.title_year
GROUP BY p.bowler, p.team
ORDER BY season_wickets DESC
LIMIT 1;
```

Result:

- ['YS Chahal', 'Rajasthan Royals', 27.0]

Verdict: [ ] correct  [ ] fix: ___

## h11 (multi_step) verified=False

**Q:** What was the home stadium of the team that finished as runners-up in the 2023 IPL season, and which city is it located in?

```sql
WITH runner_up_2023 AS (
SELECT loser AS team
FROM marts.fct_matches
WHERE season_year = 2023
  AND stage = 'Final')
SELECT 
v.venue AS home_stadium,
v.city,
COUNT(*) AS matches_played_there
FROM marts.fct_matches m
JOIN runner_up_2023 r ON (m.team1 = r.team OR m.team2 = r.team)
JOIN marts.dim_venues v ON m.venue = v.venue
WHERE m.season_year = 2023
GROUP BY v.venue, v.city
ORDER BY matches_played_there DESC
LIMIT 1;
```

Result:

- ['Narendra Modi Stadium', 'Ahmedabad', 9]

Verdict: [ ] correct  [ ] fix: ___

## h12 (comparison) verified=False

**Q:** Which bowler has claimed more career wickets in the IPL, Yuzvendra Chahal or Jasprit Bumrah?

```sql
SELECT 
bowler,
SUM(wickets) AS career_wickets
FROM marts.mart_bowling_phase
WHERE bowler IN ('YS Chahal', 'JJ Bumrah')
GROUP BY bowler
ORDER BY career_wickets DESC;
```

Result:

- ['YS Chahal', 233.0]
- ['JJ Bumrah', 187.0]

Verdict: [ ] correct  [ ] fix: ___

