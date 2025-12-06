from threading import Thread
from flask import Flask
from flask_cors import CORS
from app.sys.logger import flask_logger
from app.flask.helpers import FlaskHelpers
from app.flask.routes.local_routes import create_local_blueprint
from app.flask.routes.api_routes import create_api_blueprint
import os


def create_api_app(system) -> Flask:
    """
    Crée l'application Flask pour l'API JSON (extension navigateur).
    Accessible publiquement via reverse proxy.
    """
    log = flask_logger()

    if system:
        data_path = system.data_path
        config_path = system.config_path
        plex_root = system.plex_path
        secret_key = system.app_secret_key
    else:
        raise ValueError("system is required to create the app")

    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key

    # CORS pour l'extension (API uniquement)
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
    )

    # Initialisation des helpers
    helpers = FlaskHelpers(data_path, config_path, plex_root)
    helpers.init_db()

    # Enregistrement du blueprint API uniquement
    api_bp = create_api_blueprint(helpers=helpers, system=system)
    app.register_blueprint(api_bp)

    log.info("Application Flask API initialisée (port public)")
    return app


def create_local_app(system) -> Flask:
    """
    Crée l'application Flask pour l'interface locale admin.
    Accessible uniquement en localhost (127.0.0.1).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "templates")
    
    app = Flask(
        __name__,
        template_folder=template_dir,
    )

    log = flask_logger()

    if system:
        data_path = system.data_path
        config_path = system.config_path
        plex_root = system.plex_path
        secret_key = system.app_secret_key
        local_admin_password_hash = system.local_admin_password_hash
    else:
        raise ValueError("system is required to create the app")

    app.config["SECRET_KEY"] = secret_key
    
    # Configuration de la session : expiration après 5 minutes d'inactivité
    app.config["PERMANENT_SESSION_LIFETIME"] = 300  # 5 minutes en secondes

    # Initialisation des helpers
    helpers = FlaskHelpers(data_path, config_path, plex_root)
    helpers.init_db()

    # Enregistrement du blueprint local uniquement
    local_bp = create_local_blueprint(
        helpers=helpers,
        app_config=app.config,
        plex_root=plex_root,
        config_path=config_path,
        local_admin_password_hash=local_admin_password_hash,
        system=system,
    )
    app.register_blueprint(local_bp)

    log.info("Application Flask locale initialisée (localhost uniquement)")
    return app


class FlaskServer:
    """
    Gestionnaire du serveur Flask
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False, system: None = None, app_type: str = "api"):
        """
        Initialise le serveur Flask

        Args:
            host: Adresse IP du serveur (par défaut: 0.0.0.0)
            port: Port du serveur (par défaut: 5000)
            debug: Mode debug (par défaut: False)
            system: Instance de check_sys
            app_type: Type d'application ("api" ou "local", par défaut: "api")
        """
        self.logger = flask_logger()
        self.host = host
        self.port = port
        self.debug = debug
        self.system = system
        self.app_type = app_type
        self.app = None
        self.thread = None
        self._running = False

    def start(self):
        """
        Démarre le serveur Flask dans un thread séparé
        """
        if self._running:
            self.logger.warning("Le serveur Flask est déjà en cours d'exécution")
            return

        try:
            # Créer l'application Flask selon le type
            if self.app_type == "api":
                self.app = create_api_app(system=self.system)
            elif self.app_type == "local":
                self.app = create_local_app(system=self.system)
            else:
                raise ValueError(f"Type d'application invalide: {self.app_type}. Utilisez 'api' ou 'local'.")

            # Démarrer le serveur dans un thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self._running = True

            self.logger.info(f"Serveur Flask {self.app_type} démarré sur http://{self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du serveur Flask: {e}")
            raise

    def _run_server(self):
        """
        Fonction exécutée dans le thread pour lancer le serveur
        """
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,  # Désactiver le reloader en mode thread
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du serveur Flask: {e}")
            self._running = False

    def is_running(self):
        """
        Vérifie si le serveur est en cours d'exécution
        """
        return self._running

