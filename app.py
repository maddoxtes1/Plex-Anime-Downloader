import logging
import src.function as Function


class app:
    def __init__(self):
        system = Function.check_sys_file()
        path_list = system.path_list
        plex_list = system.plex_list
        logger = logging.getLogger(f"Starting:")

        logger.info(msg="initialisation de la queue...")
        queues = Function.Queue.queues(path_list=path_list, plex_list=plex_list, file_template=system.file_template, folder_template=system.folder_template, nombre_threads=system.settings_list[1])


        while True:
            logger.info(msg="initialisation du scan...")
            Function.Scan.scan(scan_option=system.scan_option_list, queues=queues, path_list=path_list)
            Function.countdown_timer(seconds=system.settings_list[2])






if __name__ == "__main__":
    app()