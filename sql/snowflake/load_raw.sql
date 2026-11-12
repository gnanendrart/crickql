-- Load (or reload) match files from a stage into RAW.MATCHES_JSON.
-- {stage} is CRICSHEET_S3/dt=YYYY-MM-DD/ or CRICSHEET_INTERNAL, filled in by load_snowflake.py.
-- Each match_id keeps only its newest copy: delete the files being reloaded, then COPY with
-- FORCE so a corrected Cricsheet file replaces the old row.

DELETE FROM CRICKQL.RAW.MATCHES_JSON
WHERE split_part(file_name, '/', -1) IN (
    SELECT split_part(metadata$filename, '/', -1) FROM @CRICKQL.RAW.{stage}
);

COPY INTO CRICKQL.RAW.MATCHES_JSON (file_name, doc)
FROM (SELECT metadata$filename, $1 FROM @CRICKQL.RAW.{stage})
PATTERN = '.*[.]json([.]gz)?'  -- internal stage PUT gzips files
FORCE = TRUE
ON_ERROR = 'ABORT_STATEMENT';

SELECT count(*) AS matches_json_rows FROM CRICKQL.RAW.MATCHES_JSON;
