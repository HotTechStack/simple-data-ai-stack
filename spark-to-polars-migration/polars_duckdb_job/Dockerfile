FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/project

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY polars_duckdb_job.py /opt/project/polars_duckdb_job.py

ENTRYPOINT ["python", "/opt/project/polars_duckdb_job.py"]
