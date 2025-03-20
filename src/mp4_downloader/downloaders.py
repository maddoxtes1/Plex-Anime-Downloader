import urllib3
import os
import time
import logging
import concurrent.futures
import requests
import re

class mp4_downloader:
    def __init__(self, headers, url, file_name):
        self.logger = logging.getLogger("MP4 Downloader")
        try:
            http = urllib3.PoolManager()
            urllib3_logger = logging.getLogger("urllib3")
            urllib3_logger.setLevel(logging.WARNING)
            start_byte = os.path.getsize(file_name) if os.path.exists(file_name) else 0
            headers["Range"] = f"bytes={start_byte}-"

            response = http.request('GET', url, headers=headers, preload_content=False)
            if response.status == 200:
                self.logger.info("Téléchargement complet (HTTP 200).")
                start_byte = 0
            elif response.status == 206:
                self.logger.info("Reprise du téléchargement (HTTP 206).")
            elif response.status == 416:
                self.logger.warning("Plage invalide, tentative de téléchargement complet.")
                if os.path.exists(file_name):
                    os.remove(file_name)
                self.logger.info(f"Fichier local {file_name} supprimé.")
                headers.pop("Range", None) 
                response = http.request("GET", url, headers=headers, preload_content=False)
                if response.status != 200:
                    self.logger.error(f"Erreur HTTP {response.status} après tentative de téléchargement complet.")
                    return
            else:
                self.logger.error(f"Erreur HTTP {response.status} pour l'URL {url}")
                return
            
            content_range = response.headers.get("Content-Range")
            if content_range:
                total_size = int(content_range.split("/")[-1])
                if start_byte >= total_size:
                    self.logger.info(f"Le fichier est déjà complet. Aucun téléchargement nécessaire.")
                    self.status = True
                    return
                
            with open(file_name, "ab") as f:
                block_size = 512 * 1024

                total_bytes = 0
                start_time = time.time()

                for data in response.stream(block_size):
                    f.write(data)
                    total_bytes += len(data)


                    elapsed_time = time.time() - start_time
                    if elapsed_time > 1:  # On ajuste toutes les secondes
                        current_speed = total_bytes / elapsed_time

                        # Ajustement dynamique du block_size
                        if current_speed < 1 * 1024 * 1024:  # Moins de 1 Mo/s
                            block_size = 256 * 1024  # 256 Ko
                        elif current_speed < 5 * 1024 * 1024:  # Entre 1 et 5 Mo/s
                            block_size = 512 * 1024  # 512 Ko
                        else:
                            block_size = 1024 * 1024  # 1 Mo
                        total_bytes = 0
                        start_time = time.time()
            self.status = True
        except Exception as e:
            self.logger.error(f"Erreur lors du téléchargement : {e}")
            return

class Segment_Downloader:
    def __init__(self, segments, segments_txt, headers):
        self.segments = segments
        self.segments_txt = segments_txt
        self.headers = headers
        self.logger = logging.getLogger("Segment Downloader")
        self.max_retries = 3
        self.timeout = 30
        self.chunk_size = 1048576  # 1MB chunks
        self.max_workers = min(4, len(segments))  # Adapte le nombre de workers au nombre de segments

    def get_existing_segments(self):
        """Récupère la liste des segments déjà téléchargés"""
        try:
            if os.path.exists(self.segments_txt):
                with open(self.segments_txt, 'r') as f:
                    existing_files = [line.split("'")[1] for line in f if line.startswith("file '")]
                return set(existing_files)
            return set()
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture du fichier segments.txt: {e}")
            return set()

    def update_segments_txt(self, new_segment):
        """Ajoute un nouveau segment au fichier segments.txt en maintenant l'ordre numérique"""
        try:
            # Récupère tous les segments existants
            existing_segments = []
            if os.path.exists(self.segments_txt):
                with open(self.segments_txt, 'r') as f:
                    existing_segments = [line.split("'")[1] for line in f if line.startswith("file '")]
            
            # Ajoute le nouveau segment
            existing_segments.append(new_segment)
            
            # Trie les segments par numéro
            sorted_segments = sorted(
                existing_segments,
                key=lambda x: int(re.search(r'seg-(\d+)', x).group(1)) if re.search(r'seg-(\d+)', x) else float('inf')
            )
            
            # Réécrit le fichier avec tous les segments dans l'ordre
            with open(self.segments_txt, 'w') as file_list:
                for segment in sorted_segments:
                    file_list.write(f"file '{segment}'\n")
            
            self.logger.debug(f"Segment ajouté et fichier segments.txt mis à jour dans l'ordre: {new_segment}")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout du segment au fichier segments.txt: {e}")

    def download_segment(self, url, filename, retry_count=0):
        try:
            # Vérifie si le segment existe déjà si oui le supprime
            if os.path.exists(filename):
                os.remove(filename)
                self.logger.debug(f"Segment {filename} déjà téléchargé a été supprimé")

            response = requests.get(url, stream=True, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Vérifie l'espace disponible de manière compatible avec tous les OS
            content_length = int(response.headers.get('content-length', 0))
            if content_length > 0:
                import shutil
                free_space = shutil.disk_usage(os.path.dirname(filename)).free
                if content_length > free_space:
                    raise OSError(f"Espace disque insuffisant pour {filename}")

            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        file.write(chunk)
            
            if os.path.getsize(filename) == 0:
                self.logger.error(f"Le segment {filename} est vide")
                return False
            
            # Ajoute le nouveau segment au fichier segments.txt
            self.update_segments_txt(filename)
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors du téléchargement du fichier {url}: {e}")
            if retry_count < self.max_retries:
                self.logger.error(f"Tentative de reprise {retry_count + 1}/{self.max_retries}")
                time.sleep(2 ** retry_count)  # Backoff exponentiel
                return self.download_segment(url, filename, retry_count + 1)
            return False
        except OSError as e:
            self.logger.error(f"Erreur système lors de l'écriture du fichier {filename}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors du téléchargement de {url}: {e}")
            return False

    def download_segments_in_parallel(self):
        # Récupère les segments déjà téléchargés
        existing_segments = self.get_existing_segments()
        
        # Filtre les segments à télécharger
        segments_to_download = [
            (url, filename) for url, filename in self.segments 
            if filename not in existing_segments
        ]
        
        if not segments_to_download:
            self.logger.info("Tous les segments sont déjà téléchargés")
            return True
            
        self.logger.info(f"Démarrage du téléchargement de {len(segments_to_download)} segments")
        
        failed_segments = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_segment = {
                executor.submit(self.download_segment, url, filename): (url, filename) 
                for url, filename in segments_to_download
            }
            
            for future in concurrent.futures.as_completed(future_to_segment):
                url, filename = future_to_segment[future]
                try:
                    success = future.result()
                    if not success:
                        failed_segments.append((url, filename))
                except Exception as e:
                    self.logger.error(f"Erreur lors du téléchargement de {url}: {e}")
                    failed_segments.append((url, filename))

        if failed_segments:
            self.logger.error(f"{len(failed_segments)} segments ont échoué. Tentative de reprise...")
            for url, filename in failed_segments:
                if not self.download_segment(url, filename):
                    self.logger.error(f"Échec définitif du téléchargement de {url}")
                    return False
        
        return True