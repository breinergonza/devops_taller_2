"""Utilidades pequenas para enriquecer la telemetria de New Relic."""
import os

from flask import current_app, request

try:
    import newrelic.agent
except Exception:  # pragma: no cover - solo lo uso como tolerancia operativa.
    newrelic = None


def add_custom_attribute(name, value):
    """Agrego un atributo custom sin romper la request si New Relic no esta activo."""
    if value is None or newrelic is None:
        return

    try:
        newrelic.agent.add_custom_attribute(name, value)
    except Exception:
        current_app.logger.debug(
            "No pude enviar el atributo custom de New Relic: %s", name
        )


def record_request_context():
    """Registro contexto basico para filtrar transacciones en New Relic."""
    route = request.url_rule.rule if request.url_rule else "unmatched"
    add_custom_attribute("environment", current_app.config.get("ENVIRONMENT"))
    add_custom_attribute("request_method", request.method)
    add_custom_attribute("request_endpoint", request.endpoint)
    add_custom_attribute("request_route", route)

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        add_custom_attribute("client_ip_source", "x-forwarded-for")


def new_relic_status():
    """Expongo estado seguro de configuracion sin revelar la licencia."""
    return {
        "enabled": bool(os.environ.get("NEW_RELIC_LICENSE_KEY")),
        "app_name": os.environ.get("NEW_RELIC_APP_NAME", "devops-taller-4-flask"),
        "environment": os.environ.get("NEW_RELIC_ENVIRONMENT", "development"),
        "config_file": os.environ.get("NEW_RELIC_CONFIG_FILE", "newrelic.ini"),
    }
