FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data_sources ./data_sources
COPY artifacts ./artifacts

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "mdm_pipeline.pipeline"]
