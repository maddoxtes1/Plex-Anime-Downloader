import src.function.anime_sama as anime_sama
import logging

class start:
    def __init__(self, queues, anime_json, episode_path, anime_path):
        logger = logging.getLogger(f"Anime-sama:")

        builder = anime_sama.build_url(anime_json=anime_json)
        anime_infos = builder.anime_info
        queue = []
        if anime_infos:
            for anime_info in anime_infos:
                logger = logging.getLogger(f"Anime-sama {anime_info[1]} s{anime_info[2]}:")
                episode_json = f"{episode_path}/{anime_info[1]}-s{anime_info[2]}.json"
                episode_js = f"{episode_path}/{anime_info[1]}-s{anime_info[2]}-episode.js"
                Anime_json = f"{anime_path}/{anime_info[1]}-s{anime_info[2]}.json"

                download = anime_sama.find_episode(anime_info=anime_info, episode_js=episode_js)
                is_download = download.is_download
                if is_download == True:
                    anime_sama.extract_link(episode_json=episode_json, episode_js=episode_js, logger=logger)

                    compare = anime_sama.compare_json(episode_json=episode_json, Anime_json=Anime_json)
                    new_episode = compare.new_episode
                    if new_episode:

                        queue.append((anime_info, new_episode, Anime_json))

                    for numb, link in new_episode:
                        logger.info(f"nouveaux episode detecté, episode {numb}")
                logger.info(f"scan terminer")
            for anime_info, new_episode, Anime_json in queue:    
                queues.add_to_queue(anime_info=anime_info, new_episode=new_episode, anime_json=Anime_json)
            logger = logging.getLogger(f"Anime-sama:")
            logger.info(f"scan finish")
        else:
            logger.warning(f"anime.json is empty")
