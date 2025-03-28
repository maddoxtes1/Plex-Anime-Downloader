from .json import *
from .scrap import *
import os

from ...sys.logger import universal_logger
from ...sys.function import get_path

def anime_sama_run(queues, anime_json, plex_path, download_path):
    logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")

    url_builded = build_url(anime_json=anime_json)
    anime_infos = url_builded.anime_info
    queue = []
    if anime_infos:
        for anime_info in anime_infos:
            log = universal_logger(name=f"Anime-sama - {anime_info[1]} s{anime_info[2]}", log_file="anime-sama.log")

            folder_name = get_path(langage=anime_info[3])
            if folder_name is None:
                log.warning(f"Aucun dossier trouvé avec le langage '{anime_info[3]}'")
                continue
            
            path_name = os.path.join(plex_path, folder_name)
            season_name = f"season {anime_info[2]}"
            path_list = (folder_name, anime_info[1], season_name)
            episode_js = f"{download_path}/episode/{anime_info[1]}-s{anime_info[2]}-episode.js"

            download = find_episode(anime_name=anime_info[1], anime_url=anime_info[0], episode_js=episode_js)
            if download == True:
                extract_link(path_list=path_list, episode_js=episode_js)
                uninstalled = get_unistalled_episode(path_list=path_list)
                if uninstalled:
                    for episode_name, episode_url in uninstalled:
                        log.info(f"nouveaux episode detecté: {episode_name}")
                        episode_path = f"{path_name}/{anime_info[1]}/{season_name}/{episode_name}"
                        path = (episode_path, folder_name, anime_info[1], season_name)
                        queue.append((episode_name, path, episode_url))

        for episode_name, path, episode_urls in queue:
            queues.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_urls)
        logger.info(f"scan finish")
    else:
        logger.warning(f"anime.json is empty")
