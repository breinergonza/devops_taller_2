#!/bin/bash
set -e

echo "======== Pre-deployment checks ========"
echo "Task Definition: $TASK_DEFINITION"
echo "Service: $SERVICE"
echo "Cluster: $CLUSTER"

# Aquí podrían ir validaciones previas si es necesario
echo "Pre-deployment checks passed!"
