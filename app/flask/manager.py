from threading import Thread
from flask import Flask
from werkzeug.security import generate_password_hash
from flask_cors import CORS
from app.sys.logger import flask_logger
from app.flask.helpers import FlaskHelpers
from app.flask.routes.local_routes import create_local_blueprint
from app.flask.routes.api_routes import create_api_blueprint
import os


def create_app(system) -> Flask:
    """
    Crée et configure l'application Flask pour :
    - l'interface locale admin (type Vaultwarden)
    - l'API JSON consommée par l'extension navigateur

    data_path doit correspondre à DATA dans ton conteneur (même valeur que check_sys.data_path).
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
        local_admin_password = system.local_admin_password
    else:
        raise ValueError("system is required to create the app debug: line 39 in flask/manager.py")

    app.config["SECRET_KEY"] = secret_key

    # Mot de passe admin local (ENV obligatoire en prod)
    app.config["LOCAL_ADMIN_PASSWORD_HASH"] = generate_password_hash(local_admin_password)

    # CORS pour l'extension (API uniquement)
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
    )

    # Initialisation des helpers
    helpers = FlaskHelpers(data_path, config_path, plex_root)
    helpers.init_db()

    # Enregistrement des blueprints
    local_bp = create_local_blueprint(
        helpers=helpers,
        app_config=app.config,
        plex_root=plex_root,
        config_path=config_path,
    )
    app.register_blueprint(local_bp)

    api_bp = create_api_blueprint(helpers=helpers)
    app.register_blueprint(api_bp)

    log.info("Application Flask initialisée (admin local + API extension)")
    return app


class FlaskServer:
    """
    Gestionnaire du serveur Flask
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False, system: None = None):
        """
        Initialise le serveur Flask

        Args:
            host: Adresse IP du serveur (par défaut: 0.0.0.0)
            port: Port du serveur (par défaut: 5000)
            debug: Mode debug (par défaut: False)
            data_path: Chemin vers le dossier de données (DATA) de l'application
        """
        self.logger = flask_logger()
        self.host = host
        self.port = port
        self.debug = debug
        self.system = system
        self.app = None
        self.thread = None
        self.system = system
        self._running = False

    def start(self):
        """
        Démarre le serveur Flask dans un thread séparé
        """
        if self._running:
            self.logger.warning("Le serveur Flask est déjà en cours d'exécution")
            return

        try:
            # Créer l'application Flask avec le chemin DATA fourni
            self.app = create_app(system=self.system)

            # Démarrer le serveur dans un thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self._running = True

            self.logger.info(f"Serveur Flask démarré sur http://{self.host}:{self.port}")
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

