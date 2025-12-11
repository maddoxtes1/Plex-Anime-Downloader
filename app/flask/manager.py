"""
Gestionnaire principal pour lancer les serveurs Flask (API et Dashboard)
Fusionne les fonctionnalités de waitress.py et manager.py
"""
from threading import Thread
from waitress import serve
from app.sys import FolderConfig, universal_logger, LoggerConfig
from app.flask.api.flask import create_api_app
from app.flask.dashboard.flask import create_dashboard_app


class FlaskManager:
    """
    Gestionnaire principal pour lancer les 2 serveurs Flask (API et Dashboard)
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire Flask
        """
        self.logger = universal_logger("FlaskManager", "flask.log")
        
        # Configuration des serveurs depuis les variables d'environnement
        from app.sys import EnvConfig
        from werkzeug.security import generate_password_hash
        import os
        
        # Récupérer use_waitress depuis EnvConfig
        self.use_waitress = EnvConfig.get_env("use_waitress")
        
        # Hash du mot de passe admin local (hashé à chaque démarrage)
        local_admin_password = EnvConfig.get_env("local_admin_password")
        self.local_admin_password_hash = generate_password_hash(local_admin_password)
        self.logger.info("Mot de passe admin local hashé au démarrage")
        
        # API Server
        self.api_host = os.getenv("API_HOST") or "0.0.0.0"
        self.api_port = int(os.getenv("API_PORT") or "5000")
        self.api_threads = int(os.getenv("API_THREADS") or "4")
        
        # Dashboard Server
        self.dashboard_host = os.getenv("DASHBOARD_HOST") or "0.0.0.0"
        self.dashboard_port = int(os.getenv("DASHBOARD_PORT") or "5001")
        self.dashboard_threads = int(os.getenv("DASHBOARD_THREADS") or "4")
        
        # Applications Flask
        self.api_app = None
        self.dashboard_app = None
        
        # Threads
        self.api_thread = None
        self.dashboard_thread = None
        
        # État
        self._api_running = False
        self._dashboard_running = False
    
    def start(self):
        """
        Démarre les 2 serveurs Flask (API et Dashboard)
        """
        if self._api_running or self._dashboard_running:
            self.logger.warning("Un ou plusieurs serveurs Flask sont déjà en cours d'exécution")
            return
        
        try:
            # Créer les applications Flask
            self.api_app = create_api_app()
            self.dashboard_app = create_dashboard_app()
            
            # Démarrer l'API
            self.api_thread = Thread(target=self._run_api_server, daemon=True)
            self.api_thread.start()
            self._api_running = True
            
            # Démarrer le Dashboard
            self.dashboard_thread = Thread(target=self._run_dashboard_server, daemon=True)
            self.dashboard_thread.start()
            self._dashboard_running = True
            
            self.logger.info(f"✅ Serveur API démarré sur http://{self.api_host}:{self.api_port}")
            self.logger.info(f"✅ Serveur Dashboard démarré sur http://{self.dashboard_host}:{self.dashboard_port}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage des serveurs Flask: {e}")
            raise
    
    def _run_api_server(self):
        """
        Fonction exécutée dans le thread pour lancer le serveur API
        """
        try:
            if self.use_waitress:
                serve(
                    self.api_app,
                    host=self.api_host,
                    port=self.api_port,
                    threads=self.api_threads,
                )
            else:
                self.api_app.run(
                    host=self.api_host,
                    port=self.api_port,
                    debug=False,
                    use_reloader=False,
                )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du serveur API: {e}")
            self._api_running = False
    
    def _run_dashboard_server(self):
        """
        Fonction exécutée dans le thread pour lancer le serveur Dashboard
        """
        try:
            if self.use_waitress:
                serve(
                    self.dashboard_app,
                    host=self.dashboard_host,
                    port=self.dashboard_port,
                    threads=self.dashboard_threads,
                )
            else:
                self.dashboard_app.run(
                    host=self.dashboard_host,
                    port=self.dashboard_port,
                    debug=False,
                    use_reloader=False,
                )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution du serveur Dashboard: {e}")
            self._dashboard_running = False
    
    def is_running(self):
        """
        Vérifie si les serveurs sont en cours d'exécution
        
        Returns:
            dict: {"api": bool, "dashboard": bool}
        """
        return {
            "api": self._api_running,
            "dashboard": self._dashboard_running
        }


def flask_manager():
    """
    Fonction de convenance pour créer et démarrer le gestionnaire Flask
    
    Returns:
        FlaskManager: Instance du gestionnaire démarré
    """
    manager = FlaskManager()
    manager.start()
    return manager
