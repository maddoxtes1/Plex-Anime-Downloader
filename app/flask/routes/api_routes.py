"""
Routes pour l'API JSON (extension navigateur)
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash


def create_api_blueprint(helpers):
    """
    Crée le blueprint pour les routes API.
    
    Args:
        helpers: Instance de FlaskHelpers
    """
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    @api_bp.route("/ping", methods=["GET"])
    def api_ping():
        """Permet à l'extension de tester la connexion au serveur."""
        return jsonify({"ok": True, "message": "pong"}), 200

    @api_bp.route("/login", methods=["POST"])
    def api_login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return (
                jsonify(
                    {"ok": False, "error": "username et password obligatoires"},
                ),
                400,
            )

        user = helpers.get_user_by_username(username)
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"ok": False, "error": "identifiants invalides"}), 401

        return jsonify({"ok": True, "user": username}), 200

    @api_bp.route("/dashboard", methods=["GET"])
    def api_dashboard():
        """Retourne un 'dashboard' JSON simple pour l'extension."""
        username = request.args.get("user") or "inconnu"
        return jsonify(
            {
                "ok": True,
                "user": username,
                "data": {
                    "title": "Dashboard API",
                    "message": f"Bienvenue sur ton dashboard, {username} !",
                },
            }
        ), 200

    return api_bp

