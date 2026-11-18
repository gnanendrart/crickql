# CrickQL API + seed image. One image, two roles:
#   api   uvicorn api.main:app
#   seed  bash scripts/seed.sh   (download/parse/load, dbt build, read-only role)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Exact versions from the image that passed the fresh-clone check (seed PASS=63, /query verified).
COPY requirements-api.lock .
RUN pip install -r requirements-api.lock

COPY . .

# Bake the dbt manifest into the image so /schema works before the database is seeded.
# dbt parse reads files only; it does not connect.
RUN dbt parse --project-dir dbt --profiles-dir dbt --target pg --quiet

RUN useradd --create-home crickql && chown -R crickql /app
USER crickql

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
