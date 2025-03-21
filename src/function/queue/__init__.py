import os
import threading
import queue
import logging
import shutil
from src.mp4_downloader.manager import manager
from src.function.queue.wirte_anime_json import _wirte_in_anime_json

class queues:
    def __init__(self, path_list, plex_list, file_template, folder_template, nombre_threads):
        self.logger = logging.getLogger(f"Queue:")
        self.download_queue = queue.Queue()
        self.threads = []
        self.path_list = path_list
        self.file_template = file_template
        self.folder_template = folder_template
        self.vostfr_path = plex_list[1]
        self.vf_path = plex_list[0]
        self.nombre_threads = nombre_threads
        self._initialize_threads()

    def _initialize_threads(self):
        for _ in range(self.nombre_threads):
            thread = threading.Thread(target=self._gestionnaire_queue, daemon=True)
            thread.start()
            self.logger.info(msg=f"threads-{_} started")
            self.threads.append(thread)
    
    def _gestionnaire_queue(self):
        while True:
            try:
                episode_info, episode_urls = self.download_queue.get(timeout=1)
                name, episode_number, episode_path, anime_json = episode_info
                logger = logging.getLogger(f"{name} {episode_number}:")

                for url in episode_urls:
                    if url != "none":
                        logger.info(f"Téléchargement commencé")
                        download_manager = manager(download_path=self.path_list[3], url=url)
                        if download_manager.status == True:
                            file_path = download_manager.file_name
                            if os.path.exists(file_path):
                                try:
                                    shutil.move(file_path, episode_path)
                                    logger.info(f"Téléchargement terminé")
                                    break
                                except Exception as e:
                                    logger.error(f"Erreur lors du déplacement du fichier: {e}")
                                    
                _wirte_in_anime_json(number=episode_number, url=url, anime_json=anime_json)
                self.download_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erreur inattendue dans le gestionnaire de queue : {e}")

    def add_to_queue(self, anime_info, new_episode, anime_json):
        logger = logging.getLogger(f"anime: {anime_info[1]} season {anime_info[2]}")
        folder_template = self.folder_template.format(name=anime_info[1], season=anime_info[2])
        if anime_info[3] == "vostfr":
            anime_path = f"{self.vostfr_path}/{folder_template}/"
        elif anime_info[3] == "vf" or "vf1" or "vf2":
            anime_path = f"{self.vf_path}/{folder_template}/"
        else:
            logger.warning(f"langage not supported: {anime_info[3]}")
            return
        
        if not os.path.exists(anime_path):
            os.makedirs(anime_path)

        for number, episode_urls in new_episode:
            file_template = self.file_template.format(name=anime_info[1], season=anime_info[2], episode=f"{int(number):02d}")
            episode_path = f"{anime_path}{file_template}.mp4"

            episode_info = ((f"{anime_info[1]} season {anime_info[2]}", f"{int(number):02d}", episode_path, anime_json))
            
            self.download_queue.put((episode_info, episode_urls))
    
    