FROM public.ecr.aws/docker/library/python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Defaults no secretos de New Relic; la licencia va en runtime.
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini \
    NEW_RELIC_APP_NAME="devops-taller-4-flask" \
    NEW_RELIC_LOG=stdout \
    NEW_RELIC_LOG_LEVEL=info \
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true \
    ENABLE_ERROR_TEST_ENDPOINT=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from urllib import request; request.urlopen('http://localhost:5000/ping', timeout=5)"

# Inicio Gunicorn con el wrapper de New Relic.
ENTRYPOINT ["newrelic-admin", "run-program", \
            "gunicorn", "--bind", "0.0.0.0:5000", \
            "--workers", "2", "--access-logfile", "-", \
            "application:application"]
