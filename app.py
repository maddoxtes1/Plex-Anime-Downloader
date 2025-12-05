from app.sys import check_sys, sys_logger, init_path
from app.queue.manager import queues
from app.streaming.manager import streaming_manager
from app.flask.manager import FlaskServer, create_api_app, create_local_app
from app.flask.waitress import WaitressServer
import time
import os
import sys


class App:
    def __init__(self):
        system = check_sys()
        sys_log = sys_logger()

        init_path(plex_path_json=system.plex_path_file)

        sys_log.info(msg="initialisation de la queue...")
        queue_manager = queues(
            nombre_threads=system.threads,
            download_path=system.download_path,
        )

        # Vérifier si on utilise Waitress (production) ou le serveur de développement
        use_waitress = os.getenv("USE_WAITRESS", "true").lower() == "true"

        if use_waitress:
            sys_log.info(msg="initialisation des serveurs Waitress (production)...")
            
            # Créer les applications Flask
            api_app = create_api_app(system=system)
            local_app = create_local_app(system=system)
            
            # Démarrer le serveur API (port 5000)
            api_server = WaitressServer(host="0.0.0.0", port=5000, app=api_app, threads=4)
            api_server.start()
            
            # Démarrer le serveur local (port 5001)
            local_server = WaitressServer(host="0.0.0.0", port=5001, app=local_app, threads=4)
            local_server.start()
            
            sys_log.info(msg="Serveurs Waitress démarrés (API:5000, Local:5001)")
        else:
            sys_log.info(msg="initialisation des serveurs flask (développement)...")
            # Serveur API (public, accessible via reverse proxy)
            api_server = FlaskServer(host="0.0.0.0", port=5000, debug=False, system=system, app_type="api")
            api_server.start()
            
            # Serveur local (port séparé, ne PAS exposer dans le reverse proxy)
            local_server = FlaskServer(host="0.0.0.0", port=5001, debug=False, system=system, app_type="local")
            local_server.start()

        sys_log.info(msg="initialisation des sites de streamings...")
        streaming_manager(
            queue=queue_manager,
            download_path=system.download_path,
            plex_path=system.plex_path,
            anime_json=system.anime_json,
            scan_option=system.scan_option_list,
            timer=system.timer,
        )
        
        # Garder le thread principal actif
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys_log.info("Arrêt de l'application...")


if __name__ == "__main__":
    app = App()