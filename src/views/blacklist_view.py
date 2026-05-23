"""
Recursos REST del microservicio de listas negras.

Endpoints:
    GET  /ping                          -> health check publico (sin token)
    POST /blacklists                    -> agrega un email a la lista negra
    GET  /blacklists/<string:email>     -> consulta si un email esta bloqueado

Autenticacion: Bearer Token estatico (definido en app.config['STATIC_BEARER']).
"""
from datetime import datetime

from flask import current_app, request
from flask_restful import Resource

from src.main import db
from src.models.blacklist import Blacklist
from src.observability import add_custom_attribute


def _is_authorized():
    """Valida la cabecera Authorization contra el token estatico."""
    expected = f"Bearer {current_app.config.get('STATIC_BEARER', '')}"
    return request.headers.get("Authorization", "") == expected


def _payload():
    """Obtiene los campos del body sin importar el Content-Type.

    Acepta JSON (application/json), form-urlencoded y query string.
    """
    json_body = request.get_json(silent=True) or {}
    # request.values combina query args + form data
    return {
        "email": json_body.get("email") or request.values.get("email"),
        "app_uuid": json_body.get("app_uuid")
        or request.values.get("app_uuid"),
        "blocked_reason": json_body.get("blocked_reason")
        or request.values.get("blocked_reason"),
    }


class HealthCheckResource(Resource):
    """Endpoint de salud abierto (no requiere token).

    Beanstalk puede apuntar el Health Check Path a /ping para evitar
    problemas con la autenticacion.

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

    def get(self):
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }, 200


class BlacklistResource(Resource):
    """POST /blacklists - agrega un email a la lista negra global.

    ---
    tags:
      - Blacklist
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Bearer token for authentication
      - name: email
        in: formData
        type: string
        required: true
        description: Email address to blacklist
      - name: app_uuid
        in: formData
        type: string
        required: true
        description: UUID of the application making the request
      - name: blocked_reason
        in: formData
        type: string
        required: false
        description: Reason for blocking (max 255 characters)
    responses:
      201:
        description: Email successfully added to blacklist
      400:
        description: Bad request - validation error
      401:
        description: Unauthorized - invalid token
    """

    def post(self):
        if not _is_authorized():
            return {"msg": "Unauthorized"}, 401

        args = _payload()

        if not args.get("email"):
            add_custom_attribute("validation_error", "missing_email")
            return {"msg": "email es obligatorio"}, 400
        if not args.get("app_uuid"):
            add_custom_attribute("validation_error", "missing_app_uuid")
            return {"msg": "app_uuid es obligatorio"}, 400

        if args.get("blocked_reason") and len(args["blocked_reason"]) > 255:
            add_custom_attribute("validation_error", "blocked_reason_too_long")
            return {
                "msg": "blocked_reason no puede superar 255 caracteres"
            }, 400

        # Envio solo el dominio, no el email completo.
        email_domain = args["email"].split("@")[-1] if "@" in args["email"] else "invalid"
        add_custom_attribute("blacklist_email_domain", email_domain)

        # IP origen del request (X-Forwarded-For si esta detras de un ALB)
        forwarded = request.headers.get("X-Forwarded-For", "")
        request_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.remote_addr or "0.0.0.0")
        )

        entry = Blacklist(
            email=args["email"],
            app_uuid=args["app_uuid"],
            blocked_reason=args.get("blocked_reason"),
            request_ip=request_ip,
        )
        db.session.add(entry)
        db.session.commit()

        return {
            "msg": "Email agregado a la lista negra global",
            "id": entry.id,
            "email": entry.email,
            "created_at": entry.created_at.isoformat() + "Z",
        }, 201


class BlacklistByEmailResource(Resource):
    """GET /blacklists/<email> - consulta si un email esta en la lista negra.

    ---
    tags:
      - Blacklist
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: Bearer token for authentication
      - name: email
        in: path
        type: string
        required: true
        description: Email address to check
    responses:
      200:
        description: Email status retrieved
      401:
        description: Unauthorized - invalid token
    """

    def get(self, email):
        if not _is_authorized():
            return {"msg": "Unauthorized"}, 401

        # Registro el dominio consultado.
        email_domain = email.split("@")[-1] if "@" in email else "invalid"
        add_custom_attribute("blacklist_lookup_domain", email_domain)

        entry = (
            Blacklist.query.filter_by(email=email)
            .order_by(Blacklist.created_at.desc())
            .first()
        )

        if entry is None:
            return {"in_blacklist": False, "blocked_reason": None}, 200

        return {
            "in_blacklist": True,
            "blocked_reason": entry.blocked_reason,
        }, 200
