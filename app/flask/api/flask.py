"""
Application Flask pour l'API JSON (extension navigateur)
Accessible publiquement via reverse proxy.
"""
from flask import Flask
from flask_cors import CORS
from app.flask.helpers import FlaskHelpers
from app.flask.api.routes.api_routes import create_api_blueprint


def create_api_app() -> Flask:
    """
    Crée l'application Flask pour l'API JSON.
    
    Returns:
        Application Flask configurée pour l'API
    """
    from app.sys import FolderConfig, universal_logger, EnvConfig
    
    logger = universal_logger("FlaskAPI", "flask.log")
    
    # Récupérer les chemins depuis FolderConfig et EnvConfig
    data_path = FolderConfig.find_path(folder_name="database").parent
    config_path = FolderConfig.find_path(folder_name="config")
    plex_root = EnvConfig.get_env("plex_path")
    secret_key = EnvConfig.get_env("app_secret_key")
    
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key
    
    # CORS pour l'extension (API uniquement)
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
    )
    
    # Initialisation des helpers
    helpers = FlaskHelpers(data_path, config_path, plex_root)
    
    # Enregistrement du blueprint API
    api_bp = create_api_blueprint(helpers=helpers)
    app.register_blueprint(api_bp)
    
    logger.info("Application Flask API initialisée (port public)")
    return app

