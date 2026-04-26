"""
Fabrica de la aplicacion Flask para el microservicio de listas negras.

- Inicializa SQLAlchemy y JWT.
- Registra los recursos REST.
- Crea las tablas si no existen.
"""
import os

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_restful import Api

# Instancias globales (se inicializan dentro de create_app)
db = SQLAlchemy()
jwt = JWTManager()


def create_app(test_config=None):
    """Construye una instancia de la aplicacion Flask."""
    app = Flask(__name__)

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

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)
    jwt.init_app(app)

    # Recursos REST
    from src.views.blacklist_view import (
        BlacklistResource,
        BlacklistByEmailResource,
        HealthCheckResource,
    )

    api = Api(app)
    api.add_resource(HealthCheckResource, "/ping")
    api.add_resource(BlacklistResource, "/blacklists")
    api.add_resource(BlacklistByEmailResource, "/blacklists/<string:email>")

    # Endpoint raiz informativo (Beanstalk lo usa para health checks basicos)
    @app.route("/")
    def index():
        return jsonify(
            {
                "service": "blacklist-microservice",
                "status": "ok",
                "endpoints": ["/ping", "/blacklists", "/blacklists/<email>"],
            }
        )

    # Inicializar las tablas
    with app.app_context():
        from src.models.blacklist import Blacklist  # noqa: F401

        db.create_all()

    return app
