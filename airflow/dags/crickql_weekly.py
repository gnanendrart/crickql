"""CrickQL weekly pipeline.

download >> upload_s3 >> [load_pg, load_snowflake] >> [dbt_build_pg, dbt_build_snowflake]
         >> dq_summary

Airflow only orchestrates. Every step is a CLI command run in the project's own virtualenv
(/opt/crickql-venv), so the project's dependencies (dbt, boto3, snowflake) never fight with
Airflow's. The same commands work by hand, which makes any failed task easy to reproduce.

Cloud steps are switched on with the Airflow Variable `crickql_cloud` = "true". Without it
they are skipped and the Postgres path still runs end to end.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT = "/opt/crickql"
# Clear Airflow's PYTHONPATH and user site so the project venv sees only its own packages
# (otherwise Airflow's protobuf leaks into dbt and crashes it after a successful build).
CLEAN = "env -u PYTHONPATH PYTHONNOUSERSITE=1"
RUN = f"cd {PROJECT} && {CLEAN} /opt/crickql-venv/bin/python -m"
# dbt logs and build output stay inside the container, so the run never fights over file
# ownership in the mounted project folder.
DBT = (f"cd {PROJECT} && {CLEAN} /opt/crickql-venv/bin/dbt build "
       "--project-dir dbt --profiles-dir dbt --target {target} "
       "--target-path /tmp/dbt/target_{target} --log-path /tmp/dbt/logs")
# exit 99 = skipped (BashOperator skip_on_exit_code default)
CLOUD_ONLY = '[ "{{ var.value.get(\'crickql_cloud\', \'false\') }}" = "true" ] || exit 99; '

default_args = {
    "owner": "gnan",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="crickql_weekly",
    description="Cricsheet IPL -> S3 -> Postgres + Snowflake -> dbt marts",
    schedule="0 9 * * 1",  # Mondays 09:00 UTC; Cricsheet updates a few times a week in season
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["crickql"],
) as dag:
    download = BashOperator(task_id="download", bash_command=f"{RUN} src.ingest.download")

    upload_s3 = BashOperator(
        task_id="upload_s3", bash_command=CLOUD_ONLY + f"{RUN} src.ingest.upload_s3"
    )

    # The 5% row-count guard runs inside load_pg, before anything is written.
    load_pg = BashOperator(
        task_id="load_pg", bash_command=f"{RUN} src.ingest.load_pg",
        trigger_rule="none_failed",
    )
    load_snowflake = BashOperator(
        task_id="load_snowflake",
        bash_command=CLOUD_ONLY + f"{RUN} src.ingest.load_snowflake --mode external",
        trigger_rule="none_failed",
    )

    dbt_build_pg = BashOperator(task_id="dbt_build_pg", bash_command=DBT.format(target="pg"))
    dbt_build_snowflake = BashOperator(
        task_id="dbt_build_snowflake",
        bash_command=CLOUD_ONLY + DBT.format(target="snowflake"),
    )

    dq_summary = BashOperator(
        task_id="dq_summary", bash_command=f"{RUN} src.ingest.dq_summary",
        trigger_rule="none_failed",
    )

    download >> upload_s3 >> [load_pg, load_snowflake]
    load_pg >> dbt_build_pg
    load_snowflake >> dbt_build_snowflake
    [dbt_build_pg, dbt_build_snowflake] >> dq_summary
