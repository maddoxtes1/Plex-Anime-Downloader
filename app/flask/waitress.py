"""
Gestionnaire des serveurs Waitress (production WSGI)
"""
from waitress import serve
from threading import Thread
from app.sys.logger import flask_logger


class WaitressServer:
    """
    Gestionnaire du serveur Waitress
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000, app=None, threads: int = 4):
        """
        Initialise le serveur Waitress

        Args:
            host: Adresse IP du serveur (par défaut: 0.0.0.0)
            port: Port du serveur (par défaut: 5000)
            app: Application Flask à servir
            threads: Nombre de threads (par défaut: 4)
        """
        self.logger = flask_logger()
        self.host = host
        self.port = port
        self.app = app
        self.threads = threads
        self.thread = None
        self._running = False

    def start(self):
        """
        Démarre le serveur Waitress dans un thread séparé
        """
        if self._running:
            self.logger.warning("Le serveur Waitress est déjà en cours d'exécution")
            return

        if self.app is None:
            raise ValueError("L'application Flask doit être fournie")

        try:
            # Démarrer le serveur dans un thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self._running = True

            self.logger.info(f"Serveur Waitress démarré sur http://{self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage du serveur Waitress: {e}")
            raise

    def _run_server(self):
        """
        Fonction exécutée dans le thread pour lancer le serveur Waitress
        """
        try:
            serve(
                self.app,
                host=self.host,
                port=self.port,
                threads=self.threads,
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du serveur Waitress: {e}")
            self._running = False

    def is_running(self):
        """
        Vérifie si le serveur est en cours d'exécution
        """
        return self._running

