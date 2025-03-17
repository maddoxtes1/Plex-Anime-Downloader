import logging
from src.function.scan.anime_sama import start as AS

class scan:
    def __init__(self, scan_option, queues, path_list):
        logger = logging.getLogger(f"Scanning:")

        anime_json, config_file, anime_path, download_path, episode_path = path_list

        anime_sama, anime_fr = scan_option
        
        if anime_sama == True:
            logger = logging.getLogger(f"Anime-sama:")
            logger.info(msg="scan started")
            AS(queues=queues, anime_json=anime_json, episode_path=episode_path, anime_path=anime_path)
        elif anime_fr == True:
            pass
            


