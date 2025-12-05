from app.sys import check_sys, sys_logger, init_path
from app.queue.manager import queues
from app.streaming.manager import streaming_manager
from app.flask.manager import FlaskServer
import time


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

        sys_log.info(msg="initialisation des serveurs flask...")
        # Serveur API (public, accessible via reverse proxy)
        api_server = FlaskServer(host="0.0.0.0", port=5000, debug=False, system=system, app_type="api")
        api_server.start()
        
        # Serveur local (port séparé, ne PAS exposer dans le reverse proxy)
        # Accessible uniquement via localhost:5001 depuis l'hôte
        local_server = FlaskServer(host="0.0.0.0", port=5001, debug=False, system=system, app_type="local")
        local_server.start()

        sys_log.info(msg="initialisation des site de streamings...")
        streaming_manager(
            queue=queue_manager,
            download_path=system.download_path,
            plex_path=system.plex_path,
            anime_json=system.anime_json,
            scan_option=system.scan_option_list,
            timer=system.timer,
        )


if __name__ == "__main__":
    app = App()