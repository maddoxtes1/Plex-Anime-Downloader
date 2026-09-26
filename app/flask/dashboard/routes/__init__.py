"""
Routes pour le dashboard Flask
"""
from flask import Blueprint
from datetime import timedelta
from app.flask.dashboard.routes.common import check_session_expiry, prepare_dashboard_data
from app.flask.dashboard.routes.access import register_access_routes
from app.flask.dashboard.routes.planning import register_planning_routes
from app.flask.dashboard.routes.logs import register_logs_routes
from app.flask.dashboard.routes.settings import register_settings_routes
from app.flask.dashboard.routes.search import register_search_routes


def create_local_blueprint(helpers, app_config, plex_root, config_path, local_admin_password_hash):
    """
    Crée le blueprint pour les routes locales.

    Args:
        helpers: Instance de FlaskHelpers
        app_config: Configuration de l'app Flask (pour SECRET_KEY, etc.)
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
        local_admin_password_hash: Hash du mot de passe admin local

    Returns:
        Blueprint Flask configuré avec toutes les routes
    """
    local_bp = Blueprint("local", __name__)

    # Durée d'expiration de session : 5 minutes
    SESSION_TIMEOUT = timedelta(minutes=5)

    # Enregistrer la vérification de session
    check_session_expiry(local_bp, SESSION_TIMEOUT)

    # Enregistrer toutes les routes
    register_access_routes(local_bp, local_admin_password_hash)
    register_search_routes(local_bp)
    register_planning_routes(local_bp, helpers, plex_root, config_path)
    register_logs_routes(local_bp, helpers, plex_root, config_path)
    register_settings_routes(local_bp, helpers, plex_root, config_path)

    return local_bp
