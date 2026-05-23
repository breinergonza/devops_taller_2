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

# -----------------------------------------------------------------------------
# Variables de entorno NO secretas del agente de New Relic.
# Las dejo aquí como defaults razonables; las que pueden cambiar por entorno
# (NEW_RELIC_APP_NAME, NEW_RELIC_ENVIRONMENT) las sobreescribo desde
# docker-compose (.env.local) en local y desde task-def.json en Fargate.
# La NEW_RELIC_LICENSE_KEY NUNCA va en la imagen: la inyecto en runtime.
# -----------------------------------------------------------------------------
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini \
    NEW_RELIC_APP_NAME="devops-taller-4-flask" \
    NEW_RELIC_LOG=stdout \
    NEW_RELIC_LOG_LEVEL=info \
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true \
    ENABLE_ERROR_TEST_ENDPOINT=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from urllib import request; request.urlopen('http://localhost:5000/ping', timeout=5)"

# -----------------------------------------------------------------------------
# Sirvo la app con gunicorn (no con el server de desarrollo de Flask) y la envuelvo
# con 'newrelic-admin run-program' para que el agente se inicialice antes del
# fork de los workers. Este es el patrón oficial recomendado por New Relic
# para apps Python sobre gunicorn.
# -----------------------------------------------------------------------------
ENTRYPOINT ["newrelic-admin", "run-program", \
            "gunicorn", "--bind", "0.0.0.0:5000", \
            "--workers", "2", "--access-logfile", "-", \
            "application:application"]
