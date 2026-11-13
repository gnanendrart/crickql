# Schema card review (W3 D1)

Read `python -m src.agent.schema_context` as a stranger would. Issues to test against the
baseline eval. Fix only what the failures expose, so the before/after is measurable.

1. `wides` / `noballs` (mart_bowling_phase) are RUNS, not ball counts. "How many wides" will
   sum runs. Affects eval q27.
2. Batting and bowling marts are grained by team. Mid-season trades give a player two rows per
   season. Totals must GROUP BY player only. Not warned in the descriptions.
3. No full names, only Cricsheet short names. Surnames are ambiguous (RG Sharma, I Sharma,
   Abhishek Sharma). dim_players has no full-name column.
4. Phase is fixed (powerplay = overs 1-6). Wrong for rain-shortened matches.
5. mart_batting_season has `innings` but no `matches`. "Matches played" will return innings.
6. Super-over dismissals: excluded from batting/bowling marts (matches official IPL stats).
   Still in fct_deliveries (innings 3+, is_super_over). ANSWERED: by design.
7. Home venue not modeled. Teams have multiple home grounds that change by season, and
   2009 (SA) and 2020 (UAE) were neutral. "Home record" questions are unanswerable today.
   Fix: seed team_home_venues(team, venue, season_from, season_to). Deferred to "what I'd do next".

- 
