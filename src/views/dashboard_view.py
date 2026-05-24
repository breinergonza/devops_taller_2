"""
Dashboard API endpoints para servir datos en tiempo real al frontend.
"""
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_restful import Resource, abort
from sqlalchemy import func

from src.models.blacklist import Blacklist
from src.main import db


class DashboardStatsResource(Resource):
    """Devuelve estadísticas del dashboard."""

    def get(self):
        """Obtiene KPIs y métricas del dashboard."""
        try:
            # Contar registros totales blacklisteados
            total_blacklisted = db.session.query(func.count(Blacklist.id)).scalar() or 0

            # Últimos 5 minutos
            five_min_ago = datetime.utcnow() - timedelta(minutes=5)
            recent_count = (
                db.session.query(func.count(Blacklist.id))
                .filter(Blacklist.created_at >= five_min_ago)
                .scalar()
                or 0
            )

            # Simular métricas de APM (en producción vendrían de New Relic API)
            stats = {
                "blacklisted": {
                    "total": total_blacklisted,
                    "recent_5m": recent_count,
                },
                "apdex": {
                    "value": 0.94,
                    "threshold": 0.5,
                    "state": "satisfied",  # satisfied | tolerating | frustrated
                },
                "error_rate": {
                    "percent": 0.4,
                    "errors_5xx": 2,
                    "errors_401": 7,
                    "notice_errors": 9,
                    "threshold_percent": 5.0,
                    "state": "nominal",  # nominal | warning | critical
                },
                "throughput": {
                    "req_per_min": 142,
                    "peak_today": 1840,
                },
                "latency": {
                    "p50_ms": 45,
                    "p95_ms": 118,
                    "p99_ms": 312,
                },
                "database": {
                    "select_ms": 12,
                    "insert_ms": 28,
                    "update_ms": 35,
                    "delete_ms": 18,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            return stats, 200
        except Exception as e:
            return {"error": str(e)}, 500


class DashboardEventsResource(Resource):
    """Stream de eventos de blacklist en tiempo real."""

    def get(self):
        """Obtiene últimos eventos de blacklist."""
        try:
            limit = request.args.get("limit", default=20, type=int)
            limit = min(limit, 100)

            events = (
                db.session.query(Blacklist)
                .order_by(Blacklist.created_at.desc())
                .limit(limit)
                .all()
            )

            event_list = [
                {
                    "id": e.id,
                    "email": e.email[:3] + "***@***." + e.email.split(".")[-1],
                    "app_uuid": e.app_uuid[:8] + "...",
                    "reason": e.blocked_reason or "No reason provided",
                    "timestamp": e.created_at.isoformat(),
                    "method": "POST /blacklists"
                    if e.id % 2 == 0
                    else "GET /blacklists/<email>",
                }
                for e in events
            ]
            return {"events": event_list, "count": len(event_list)}, 200
        except Exception as e:
            return {"error": str(e)}, 500


class DashboardChartDataResource(Resource):
    """Datos para gráficos del dashboard."""

    def get(self, chart_type):
        """Obtiene datos para un tipo específico de gráfico."""
        try:
            if chart_type == "latency":
                # Simular datos de latencia por hora
                data = {
                    "categories": [
                        f"{i}:00" for i in range(24)
                    ],
                    "series": [
                        {
                            "name": "p50",
                            "data": [45 + (i % 10) - 5 for i in range(24)],
                        },
                        {
                            "name": "p95",
                            "data": [118 + (i % 20) - 10 for i in range(24)],
                        },
                        {
                            "name": "p99",
                            "data": [312 + (i % 50) - 25 for i in range(24)],
                        },
                    ],
                }
            elif chart_type == "apdex":
                # Gauge de Apdex
                data = {
                    "value": 0.94,
                    "ranges": [0.7, 0.85, 1.0],
                    "state": "satisfied",
                }
            elif chart_type == "errors":
                # Timeline de errores
                data = {
                    "categories": [f"{i}:00" for i in range(24)],
                    "series": [
                        {
                            "name": "5xx",
                            "data": [0, 1, 0, 0, 2, 0, 0, 0, 0, 0, 1, 0] + [0] * 12,
                        },
                        {
                            "name": "401",
                            "data": [
                                0,
                                0,
                                0,
                                2,
                                1,
                                0,
                                3,
                                1,
                                0,
                                0,
                                0,
                                0,
                            ] + [0] * 12,
                        },
                        {
                            "name": "notice_error",
                            "data": [
                                1,
                                2,
                                0,
                                1,
                                3,
                                2,
                                0,
                                1,
                                0,
                                0,
                                0,
                                0,
                            ] + [0] * 12,
                        },
                    ],
                }
            else:
                abort(404, message=f"Unknown chart type: {chart_type}")

            return data, 200
        except Exception as e:
            return {"error": str(e)}, 500


class HealthCheckDashboardResource(Resource):
    """Health check específico para el dashboard."""

    def get(self):
        """Verifica que el dashboard pueda acceder a sus dependencias."""
        try:
            db.session.execute("SELECT 1")
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat(),
            }, 200
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }, 503
