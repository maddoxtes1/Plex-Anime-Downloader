from threading import Thread
from . import create_app
from app.sys.logger import flask_logger


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

