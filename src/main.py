"""
Fabrica de la aplicacion Flask para el microservicio de listas negras.

- Inicializa SQLAlchemy y JWT.
- Registra los recursos REST.
- Crea las tablas si no existen.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_restful import Api
from flasgger import Flasgger

from src.observability import (
    new_relic_status,
    record_request_context,
    record_response_context,
)

# Cargar variables de entorno
env_file = os.environ.get("ENV_FILE", ".env.local")
env_path = Path(__file__).parent.parent / env_file
if env_path.exists():
    load_dotenv(env_path)

from flask_socketio import SocketIO
from threading import Lock

# Instancias globales (se inicializan dentro de create_app)
db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")

thread = None
thread_lock = Lock()


def background_thread_emitter(app):
    """Bucle de segundo plano que emite métricas en tiempo real a los clientes conectados."""
    with app.app_context():
        from src.views.dashboard_view import DashboardStatsResource, DashboardEventsResource
        stats_resource = DashboardStatsResource()
        events_resource = DashboardEventsResource()
        
        while True:
            try:
                stats_data, stats_code = stats_resource.get()
                events_data, events_code = events_resource.get()
                
                if stats_code == 200 and events_code == 200:
                    socketio.emit('metrics_update', {
                        'stats': stats_data,
                        'events': events_data
                    })
            except Exception:
                pass
            socketio.sleep(3.0)


def create_app(test_config=None):
    """Construye una instancia de la aplicacion Flask."""
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    # Configuracion por defecto (puede sobreescribirse via env vars o test_config)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URI", "sqlite:///local.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.environ.get(
        "JWT_SECRET_KEY", "change-me-in-prod"
    )
    # Token estatico aceptado como Bearer (segun enunciado de la entrega 1)
    app.config["STATIC_BEARER"] = os.environ.get(
        "STATIC_BEARER", "uniandes-devops-2026"
    )
    app.config["ENVIRONMENT"] = os.environ.get("ENVIRONMENT", "local")
    app.config["ENABLE_ERROR_TEST_ENDPOINT"] = (
        os.environ.get("ENABLE_ERROR_TEST_ENDPOINT", "false").lower() == "true"
    )

    if test_config is not None:
        app.config.update(test_config)

    # Agrego contexto basico a New Relic.
    app.before_request(record_request_context)
    app.after_request(record_response_context)

    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    @socketio.on('connect')
    def handle_connect():
        global thread
        with thread_lock:
            if thread is None:
                thread = socketio.start_background_task(background_thread_emitter, app)

    # Inicializar Swagger/Flasgger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs",
    }
    flasgger = Flasgger(
        app,
        config=swagger_config,
        template={
            "swagger": "2.0",
            "info": {
                "title": "Blacklist Microservice API",
                "version": "1.0.0",
                "description": "API para gestionar listas negras de emails",
            },
        },
    )

    # Recursos REST
    from src.views.blacklist_view import (
        BlacklistResource,
        BlacklistByEmailResource,
        HealthCheckResource,
    )
    from src.views.dashboard_view import (
        DashboardStatsResource,
        DashboardEventsResource,
        DashboardChartDataResource,
        HealthCheckDashboardResource,
    )

    api = Api(app)
    api.add_resource(HealthCheckResource, "/ping")
    api.add_resource(BlacklistResource, "/blacklists")
    api.add_resource(BlacklistByEmailResource, "/blacklists/<string:email>")

    # Dashboard API endpoints
    api.add_resource(DashboardStatsResource, "/api/dashboard/stats")
    api.add_resource(DashboardEventsResource, "/api/dashboard/events")
    api.add_resource(DashboardChartDataResource, "/api/dashboard/charts/<string:chart_type>")
    api.add_resource(HealthCheckDashboardResource, "/api/dashboard/health")

    # Swagger endpoints wrapper para que Flasgger los detecte
    @app.route("/ping", methods=["GET"])
    def ping_swagger():
        """
        Health check endpoint
        ---
        tags:
          - Health
        responses:
          200:
            description: Service is healthy
            schema:
              type: object
              properties:
                status:
                  type: string
                timestamp:
                  type: string
        """
        health = HealthCheckResource()
        return health.get()

    @app.route("/blacklists", methods=["POST"])
    def blacklists_post_swagger():
        """
        Add email to blacklist
        ---
        tags:
          - Blacklist
        parameters:
          - name: Authorization
            in: header
            type: string
            required: true
            description: Bearer token
          - name: email
            in: formData
            type: string
            required: true
            description: Email to blacklist
          - name: app_uuid
            in: formData
            type: string
            required: true
            description: Application UUID
          - name: blocked_reason
            in: formData
            type: string
            required: false
            description: Reason for blocking
        responses:
          201:
            description: Email added to blacklist
          400:
            description: Bad request
          401:
            description: Unauthorized
        """
        bl = BlacklistResource()
        return bl.post()

    @app.route("/blacklists/<email>", methods=["GET"])
    def blacklists_get_swagger(email):
        """
        Check if email is blacklisted
        ---
        tags:
          - Blacklist
        parameters:
          - name: Authorization
            in: header
            type: string
            required: true
            description: Bearer token
          - name: email
            in: path
            type: string
            required: true
            description: Email to check
        responses:
          200:
            description: Email status
          401:
            description: Unauthorized
        """
        bl = BlacklistByEmailResource()
        return bl.get(email)

    # Endpoint raiz - Dashboard
    @app.route("/")
    def dashboard():
        return render_template("index.html")

    # Endpoint raiz API info (para Beanstalk health checks)
    @app.route("/api/info")
    def api_info():
        return jsonify(
            {
                "service": "blacklist-microservice",
                "status": "ok",
                "version": "1.0.0",
                "environment": app.config["ENVIRONMENT"],
                "endpoints": ["/ping", "/blacklists", "/blacklists/<email>", "/api/docs"],
            }
        )

    @app.route("/observability/newrelic")
    def observability_newrelic():
        """Devuelvo una verificacion segura de la configuracion de New Relic."""
        return jsonify(new_relic_status())

    if app.config["ENABLE_ERROR_TEST_ENDPOINT"]:
        # Activo este 500 solo para pruebas controladas.
        @app.route("/debug/newrelic-error")
        def debug_newrelic_error():
            raise RuntimeError("Error controlado para validar New Relic Errors Inbox")

    # Endpoint para poblar la base de datos con datos de ejemplo (solo local)
    if app.config["ENVIRONMENT"] == "local":
        @app.route("/debug/seed-dashboard", methods=["POST"])
        def seed_dashboard():
            """Popula la base de datos con datos de ejemplo para el dashboard."""
            from datetime import datetime, timedelta
            from src.models.blacklist import Blacklist

            try:
                # Borrar datos existentes
                Blacklist.query.delete()
                db.session.commit()

                # Datos de ejemplo
                domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'example.com', 'spam.com']
                names = ['spam', 'phishing', 'malware', 'botnet', 'scam', 'fraud', 'abuse']
                reasons = ['phishing', 'spam', 'malware', 'botnet', 'fraud', 'abuse']

                # Crear registros de ejemplo
                now = datetime.utcnow()
                entries = []

                for i in range(50):
                    hours_ago = (i % 24)
                    email = f"{names[i % len(names)]}{i}@{domains[i % len(domains)]}"
                    reason = reasons[i % len(reasons)]
                    timestamp = now - timedelta(hours=hours_ago, minutes=(i % 60))

                    entry = Blacklist(
                        email=email,
                        app_uuid=f"app-{i:04d}-uuid-{i:04d}",
                        blocked_reason=reason,
                        created_at=timestamp,
                        request_ip=f"192.168.{i % 256}.{(i * 7) % 256}"
                    )
                    entries.append(entry)

                db.session.bulk_save_objects(entries)
                db.session.commit()

                return jsonify({
                    "status": "success",
                    "message": f"Base de datos poblada con {len(entries)} registros",
                    "total": Blacklist.query.count()
                }), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

    # Inicializar las tablas
    with app.app_context():
        from src.models.blacklist import Blacklist  # noqa: F401

        db.create_all()

    return app
