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
    problemas con la autenticacion."""

    def get(self):
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }, 200


class BlacklistResource(Resource):
    """POST /blacklists - agrega un email a la lista negra global."""

    def post(self):
        if not _is_authorized():
            return {"msg": "Unauthorized"}, 401

        args = _payload()

        if not args.get("email"):
            return {"msg": "email es obligatorio"}, 400
        if not args.get("app_uuid"):
            return {"msg": "app_uuid es obligatorio"}, 400

        if args.get("blocked_reason") and len(args["blocked_reason"]) > 255:
            return {
                "msg": "blocked_reason no puede superar 255 caracteres"
            }, 400

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
    """GET /blacklists/<email> - consulta si un email esta en la lista negra."""

    def get(self, email):
        if not _is_authorized():
            return {"msg": "Unauthorized"}, 401

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
