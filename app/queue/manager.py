import threading
import queue

from .worker import _worker
from ..sys import queue_logger

class queues:
    def __init__(self, nombre_threads, download_path):
        self.logger = queue_logger()
        self.download_queue = queue.Queue()
        self.threads = []
        self.nombre_threads = nombre_threads
        self.download_path = download_path
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
    
    