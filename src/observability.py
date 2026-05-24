"""Utilidades pequenas para enriquecer la telemetria de New Relic."""
import os

from flask import current_app, request

try:
    import newrelic.agent
except Exception:  # pragma: no cover - tolerancia local.
    newrelic = None


def add_custom_attribute(name, value):
    """Envio un atributo custom si el agente esta disponible."""
    if value is None or newrelic is None:
        return

    try:
        newrelic.agent.add_custom_attribute(name, value)
    except Exception:
        current_app.logger.debug(
            "No pude enviar el atributo custom de New Relic: %s", name
        )


def record_custom_event(event_type, params):
    """Registra un evento personalizado en New Relic para analiticas."""
    if newrelic is None or not params:
        return

    try:
        newrelic.agent.record_custom_event(event_type, params)
    except Exception:
        current_app.logger.debug(
            "No pude registrar el evento personalizado en New Relic: %s", event_type
        )


def notice_error(error, attributes=None):
    """Registra un error o excepcion en New Relic con atributos opcionales."""
    if newrelic is None:
        return

    try:
        newrelic.agent.notice_error(error=error, attributes=attributes)
    except Exception:
        current_app.logger.debug(
            "No pude notificar el error a New Relic: %s", str(error)
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


def record_response_context(response):
    """after_request de Flask para enriquecer la transaccion con datos de la respuesta."""
    if newrelic is None:
        return response

    try:
        add_custom_attribute("response_status", response.status_code)
        if response.content_length is not None:
            add_custom_attribute("response_content_length", response.content_length)
        if response.content_type:
            add_custom_attribute("response_content_type", response.content_type)
    except Exception:
        pass
    return response


def new_relic_status():
    """Expongo estado seguro de configuracion sin revelar la licencia."""
    return {
        "enabled": bool(os.environ.get("NEW_RELIC_LICENSE_KEY")),
        "app_name": os.environ.get("NEW_RELIC_APP_NAME", "devops-taller-4-flask"),
        "environment": os.environ.get("NEW_RELIC_ENVIRONMENT", "development"),
        "config_file": os.environ.get("NEW_RELIC_CONFIG_FILE", "newrelic.ini"),
    }
