FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-21-jre-headless \
        procps \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/jvm/java-21-openjdk-* /usr/lib/jvm/java-21-openjdk

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk
ENV PATH="${JAVA_HOME}/bin:${PATH}"

WORKDIR /opt/project

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY spark_job.py /opt/project/spark_job.py

ENTRYPOINT ["python", "/opt/project/spark_job.py"]
