"""Configuracion compartida de pytest para los tests del microservicio.

Cada test obtiene un cliente de Flask aislado con SQLite en memoria, lo
que permite ejecutarlo en CI (CodeBuild) sin depender de PostgreSQL.
"""
import pytest

from src.main import create_app, db


@pytest.fixture
def app():
    app = create_app(
        test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_BEARER": "uniandes-devops-2026",
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_header():
    return {"Authorization": "Bearer uniandes-devops-2026"}


@pytest.fixture
def bad_auth_header():
    return {"Authorization": "Bearer token-invalido"}
