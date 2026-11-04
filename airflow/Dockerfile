# Airflow 3 plus a separate virtualenv for the project, so dbt and the ingest code never
# share dependencies with Airflow itself.
FROM apache/airflow:3.1.0-python3.11

USER root
RUN python -m venv /opt/crickql-venv && chown -R airflow: /opt/crickql-venv
USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN /opt/crickql-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
