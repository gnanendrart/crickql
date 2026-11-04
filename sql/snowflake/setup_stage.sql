-- Run once in a Snowflake worksheet as ACCOUNTADMIN (W2 D2).
-- Replace the two <...> placeholders. Nothing here contains a secret.

CREATE DATABASE IF NOT EXISTS CRICKQL;
CREATE SCHEMA IF NOT EXISTS CRICKQL.RAW;
CREATE WAREHOUSE IF NOT EXISTS DEV_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;

CREATE FILE FORMAT IF NOT EXISTS CRICKQL.RAW.CRICSHEET_JSON
    TYPE = JSON
    STRIP_OUTER_ARRAY = FALSE;

-- Option A: external stage on S3 (the production path)
-- 1. In AWS IAM create role crickql-snowflake-s3 with s3:GetObject + s3:ListBucket on the bucket.
-- 2. Create the integration, then DESC it and copy STORAGE_AWS_IAM_USER_ARN and
--    STORAGE_AWS_EXTERNAL_ID into the role's trust policy.
CREATE STORAGE INTEGRATION IF NOT EXISTS CRICKQL_S3
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::<aws_account_id>:role/crickql-snowflake-s3'
    STORAGE_ALLOWED_LOCATIONS = ('s3://<bucket>/cricsheet/');

DESC INTEGRATION CRICKQL_S3;

CREATE STAGE IF NOT EXISTS CRICKQL.RAW.CRICSHEET_S3
    STORAGE_INTEGRATION = CRICKQL_S3
    URL = 's3://<bucket>/cricsheet/ipl/'
    FILE_FORMAT = CRICKQL.RAW.CRICSHEET_JSON;

-- Option B (fallback if IAM fights you for more than 90 minutes): internal stage.
-- src/ingest/load_snowflake.py --mode internal PUTs the files here from your Mac.
CREATE STAGE IF NOT EXISTS CRICKQL.RAW.CRICSHEET_INTERNAL
    FILE_FORMAT = CRICKQL.RAW.CRICSHEET_JSON;

-- Raw landing table: one row per match file, the whole document as VARIANT.
CREATE TABLE IF NOT EXISTS CRICKQL.RAW.MATCHES_JSON (
    file_name  STRING        NOT NULL,
    loaded_at  TIMESTAMP_LTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    doc        VARIANT       NOT NULL
);
