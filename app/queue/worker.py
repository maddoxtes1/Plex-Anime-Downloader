import logging
import os
import shutil
import queue

from mp4mdl import mp4mdl
from ..sys.database import database
from ..sys.logger import queue_logger, universal_logger

def _worker(download_queue, download_path):
    logger = queue_logger()
    while True:
        try:
            episode_name, path, episode_urls = download_queue.get(timeout=1)
            episode_path, path_name, serie_name, season_name = path
            logger = logging.getLogger(f"{episode_name}:")
            status = False
            logs = universal_logger(name=f"{episode_name}:", log_file="download.log")
            logs.info(f"Téléchargement commencé")
            for url in episode_urls:
                if url != "none":
                    if not os.path.exists(os.path.dirname(episode_path)):
                        os.makedirs(os.path.dirname(episode_path))
                    downloader = mp4mdl(download_path=download_path, final_path=episode_path, url=url, logger=logs)
                    download_status = downloader.download()
                    if download_status == True:
                        status = True
                        break
            if status == True:
                logs.info(f"Téléchargement Terminé")
                db = database()
                db.update_episode(path_name=path_name, series_name=serie_name, season_name=season_name, episode_list=(episode_name, "downloaded", episode_urls))
            else:
                logs.error(f"Toutes les URLs ont échoué")
            download_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Erreur inattendue dans le worker: {e}")
