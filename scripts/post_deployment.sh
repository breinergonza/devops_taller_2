#!/bin/bash
set -e

echo "======== Post-deployment health checks ========"

# Esperar a que el contenedor esté listo (máximo 60 segundos)
HEALTH_CHECK_TIMEOUT=60
INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $HEALTH_CHECK_TIMEOUT ]; do
    if curl -f -s -X GET "http://localhost:5000/ping" > /dev/null 2>&1; then
        echo "✓ Service is healthy!"
        exit 0
    fi
    
    echo "Waiting for service to be ready... ($ELAPSED/$HEALTH_CHECK_TIMEOUT seconds)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo "✗ Service health check failed after $HEALTH_CHECK_TIMEOUT seconds"
exit 1
