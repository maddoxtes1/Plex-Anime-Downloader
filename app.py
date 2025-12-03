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

        sys_log.info(msg="initialisation du serveur flask...")
        server = FlaskServer(host="0.0.0.0",port=5000,debug=False, system=system)
        server.start()

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