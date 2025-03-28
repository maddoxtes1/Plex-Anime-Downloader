import logging
import os
import shutil
import queue

from ..mp4_downloader.manager import manager
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
            for url in episode_urls:
                if url != "none":
                    logs = universal_logger(name=f"{episode_name}:", log_file="download.log")
                    logs.info(f"Téléchargement commencé")
                    download_manager = manager(download_path=download_path, url=url, logger=logs)
                    if download_manager.status == True:
                        file_path = download_manager.file_name
                        if os.path.exists(file_path):
                            try:
                                # Exemple: '/path/to/episode.mp4' -> '/path/to'
                                if not os.path.exists(os.path.dirname(episode_path)):
                                    os.makedirs(os.path.dirname(episode_path))
                                shutil.move(file_path, episode_path)
                                logs.info(f"Téléchargement terminé")
                                status = True
                                break
                            except Exception as e:
                                logger.error(f"Erreur lors du déplacement du fichier: file-{episode_name}, error-{e}")
                                continue
                        else:
                            logger.error(f"Erreur lors du téléchargement du fichier: file-{episode_name}, error-{e}")
                            continue
                    else:
                        logger.error(f"Erreur lors du téléchargement du fichier: file-{episode_name}, error-{e}")
                        continue
                    
            if status == True:
                db = database()
                db.update_episode(path_name=path_name, series_name=serie_name, season_name=season_name, episode_list=(episode_name, "downloaded", episode_urls))
            else:
                logs.error(f"Toutes les URLs ont échoué")
            download_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Erreur inattendue dans le gestionnaire de queue : file-{episode_name}, error-{e}")