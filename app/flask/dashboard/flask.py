"""
Application Flask pour l'interface locale admin (dashboard)
Accessible uniquement en localhost (127.0.0.1).
"""
import os
from flask import Flask
from app.flask.helpers import FlaskHelpers
from app.flask.dashboard.routes import create_local_blueprint


def create_dashboard_app() -> Flask:
    """
    Crée l'application Flask pour l'interface locale admin.

    Returns:
        Application Flask configurée pour le dashboard
    """
    from app.sys import FolderConfig, universal_logger, EnvConfig
    from werkzeug.security import generate_password_hash
    import configparser

    logger = universal_logger("FlaskDashboard", "flask.log")

    # Chemin vers les templates
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "templates")

    app = Flask(
        __name__,
        template_folder=template_dir,
    )

    # Récupérer les chemins depuis FolderConfig et EnvConfig
    data_path = FolderConfig.find_path(folder_name="database").parent
    config_path = FolderConfig.find_path(folder_name="config")
    plex_root = EnvConfig.get_env("plex_path")
    secret_key = EnvConfig.get_env("app_secret_key")

    # Récupérer le mot de passe admin et le hasher
    local_admin_password = EnvConfig.get_env("local_admin_password")
    local_admin_password_hash = generate_password_hash(local_admin_password)

    app.config["SECRET_KEY"] = secret_key

    # Configuration de la session : expiration après 5 minutes d'inactivité
    app.config["PERMANENT_SESSION_LIFETIME"] = 300  # 5 minutes en secondes

    # Filtre personnalisé pour trim (supprimer les espaces en début/fin)
    @app.template_filter('trim')
    def trim_filter(s):
        """Supprime les espaces en début et fin de chaîne"""
        if isinstance(s, str):
            return s.strip()
        return s

    # Route pour servir l'icône
    @app.route('/static/icon/Plex-Anime-Downloader-icon.png')
    def serve_icon():
        from flask import send_from_directory
        # Chemin vers le dossier static/dashboard/static/icon depuis la racine du projet
        current_file = os.path.abspath(__file__)
        # Remonter jusqu'à la racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        icon_dir = os.path.join(project_root, "app", "flask", "dashboard", "static", "icon")
        return send_from_directory(icon_dir, 'Plex-Anime-Downloader-icon.png')

    # Route pour servir les images (types et langues)
    @app.route('/static/<path:path>')
    def serve_static_file(path):
        from flask import send_from_directory
        # Chemin vers le dossier static/dashboard/static depuis la racine du projet
        current_file = os.path.abspath(__file__)
        # Remonter jusqu'à la racine du projet
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
        static_dir = os.path.join(project_root, "app", "flask", "dashboard", "static", path)
        return send_from_directory(static_dir, path)

    # Initialisation des helpers
    helpers = FlaskHelpers(data_path, config_path, plex_root)

    # Enregistrement du blueprint local
    local_bp = create_local_blueprint(
        helpers=helpers,
        app_config=app.config,
        plex_root=plex_root,
        config_path=config_path,
        local_admin_password_hash=local_admin_password_hash,
    )
    app.register_blueprint(local_bp)

    logger.info("Application Flask dashboard initialisée (localhost uniquement)")
    return app
