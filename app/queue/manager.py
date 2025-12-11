import threading
import queue
from ..sys import universal_logger
from ..sys import FolderConfig
from configparser import ConfigParser

from .worker import _worker

class queues:
    def __init__(self):
        self.logger = universal_logger("Queue", "sys.log")
        self.download_queue = queue.Queue()
        self.threads = []

        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        self.nombre_threads = int(config.get("settings", "threads"))

        self.download_path = FolderConfig.find_path(folder_name="download")
        self._initialize_threads()

    def _initialize_threads(self):
        for _ in range(self.nombre_threads):
            thread = threading.Thread(target=_worker, daemon=True, args=(self.download_queue, self.download_path))
            thread.start()
            self.logger.info(msg=f"threads-{_} started")
            self.threads.append(thread)

    def add_to_queue(self, episode_name, path, episode_urls):
        # Vérifier si la série est déjà dans la queue
        for item in self.download_queue.queue:
            n, p, u = item
            if episode_name == n and path == p:
                # Si trouvé, mettre à jour les URLs et sortir
                self.download_queue.queue[self.download_queue.queue.index(item)] = (episode_name, path, episode_urls)
                self.logger.info(f"URLs mises à jour pour {episode_name}")
                return
                
        # Si pas trouvé, ajouter à la queue
        self.download_queue.put((episode_name, path, episode_urls))
        self.logger.info(f"Ajout de {episode_name} à la queue")
    
    