-- Raw layer: one row per match, one row per delivery, exactly as parsed from Cricsheet.
-- Nothing is aggregated or renamed here. dbt staging models do that.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.matches (
    match_id              bigint PRIMARY KEY,
    season_raw            text NOT NULL,      -- Cricsheet label, e.g. '2007/08'
    season_year           int NOT NULL,       -- year the matches were played, e.g. 2008
    match_date            date NOT NULL,
    event_name            text,
    match_number          int,
    stage                 text,               -- 'Final', 'Qualifier 1' ... null in league stage
    team1                 text NOT NULL,
    team2                 text NOT NULL,
    toss_winner           text,
    toss_decision         text,
    venue                 text,
    city                  text,
    result_type           text NOT NULL CHECK (result_type IN ('normal', 'dl', 'tie', 'no result')),
    winner                text,               -- for ties, the super over winner
    win_by_runs           int,
    win_by_wickets        int,
    method                text,
    decided_by_super_over boolean NOT NULL,
    target_runs           int,
    target_overs          numeric(4, 1),
    player_of_match       text,
    scheduled_overs       int,
    balls_per_over        int,
    innings_count         int NOT NULL,
    has_super_over        boolean NOT NULL,
    has_miscounted_over   boolean NOT NULL,
    data_version          text,
    source_file           text NOT NULL,
    _loaded_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.deliveries (
    match_id         bigint NOT NULL REFERENCES raw.matches (match_id),
    innings          int NOT NULL,            -- 1, 2; 3+ are super overs
    over_no          int NOT NULL,            -- 0-based, as Cricsheet stores it
    ball_seq         int NOT NULL,            -- every delivery in the over, incl. wides/no-balls
    legal_ball       int,                     -- legal ball number in the over, null if illegal
    actual_delivery  text,
    batting_team     text NOT NULL,
    bowling_team     text NOT NULL,
    is_super_over    boolean NOT NULL,
    batter           text NOT NULL,
    bowler           text NOT NULL,
    non_striker      text NOT NULL,
    runs_batter      int NOT NULL,
    runs_extras      int NOT NULL,
    runs_total       int NOT NULL,
    is_non_boundary  boolean NOT NULL,        -- a 4/6 that was run, not a boundary
    extras_wides     int NOT NULL,
    extras_noballs   int NOT NULL,
    extras_byes      int NOT NULL,
    extras_legbyes   int NOT NULL,
    extras_penalty   int NOT NULL,
    is_legal         boolean NOT NULL,
    wicket_count     int NOT NULL,
    wicket_kind      text,
    player_out       text,
    fielders         text,
    _loaded_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, innings, over_no, ball_seq)
);

-- One row per pipeline run. The Airflow row-count guard reads this table.
CREATE TABLE IF NOT EXISTS raw.load_audit (
    run_id              serial PRIMARY KEY,
    loaded_at           timestamptz NOT NULL DEFAULT now(),
    source_sha256       text,
    matches_parsed      int NOT NULL,
    matches_rejected    int NOT NULL,
    matches_inserted    int NOT NULL,
    matches_updated     int NOT NULL,
    deliveries_loaded   int NOT NULL,
    matches_total       int NOT NULL,
    deliveries_total    int NOT NULL
);
