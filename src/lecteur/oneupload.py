import requests 
from bs4 import BeautifulSoup
import logging
import src.function as Function
import re
import concurrent.futures
import os
import subprocess
import time

class SegmentDownloader:
    def __init__(self, segments, headers, logger):
        self.segments = segments
        self.headers = headers
        self.logger = logger
        self.max_retries = 3
        self.timeout = 30
        self.chunk_size = 1048576  # 1MB chunks
        self.max_workers = min(4, len(segments))  # Adapte le nombre de workers au nombre de segments

    def download_segment(self, url, filename, retry_count=0):
        try:
            response = requests.get(url, stream=True, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Vérifie l'espace disponible
            content_length = int(response.headers.get('content-length', 0))
            if content_length > 0:
                free_space = os.statvfs(os.path.dirname(filename)).f_bfree * os.statvfs(os.path.dirname(filename)).f_bsize
                if content_length > free_space:
                    raise OSError(f"Espace disque insuffisant pour {filename}")

            with open(filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        file.write(chunk)
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
        failed_segments = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_segment = {
                executor.submit(self.download_segment, url, filename): (url, filename) 
                for url, filename in self.segments
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

class oneupload_downloader:
    def __init__(self, logger, download_path, name, path, url):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            "Referer": "https://oneupload.net/"
        }
        self.logger = logger
        self.status = False
        self.temps_path = f"{download_path}/{name}"
        self.path = path
        Function.create_path(path=self.temps_path)

        if not self._initialize_download(url):
            return

    def _initialize_download(self, url):
        m3u8_url = self.get_m3u8_url(url=url)
        if not m3u8_url:
            self.logger.error("Erreur lors de la récupération de l'url m3u8 (probablement a cause que le fichier n'existe plus)")
            return False

        best_url = self.get_best_quality_url(m3u8_url=m3u8_url)
        if not best_url:
            self.logger.error("Erreur lors de la récupération de l'url de la meilleur qualité (probablement a cause que le fichier n'existe plus)")
            return False

        segment_urls = self.get_segment_urls(best_url=best_url)
        if not segment_urls:
            self.logger.error("Erreur lors de la récupération des url des segments (probablement a cause que le fichier n'existe plus)")
            return False

        segmentation_path = f"{self.temps_path}/segmentation/"
        Function.create_path(path=segmentation_path)
        segments = self.gestionaire_segmentation(segment_urls=segment_urls, segmentation_path=segmentation_path)

        downloader = SegmentDownloader(segments=segments, headers=self.headers, logger=self.logger)
        downloader.download_segments_in_parallel()

        self.create_file_list(temps_path=self.temps_path, segmentation_path=segmentation_path)
        self.merge_segments(path=self.path, temps_path=self.temps_path)
        return True

    def get_m3u8_url(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup.find_all('script'):
                if script.string:
                    match = re.search(r'file:"(https?://[^"]+\.m3u8[^"]*)"', script.string)
                    if match:
                        m3u8_url = match.group(1)
                        return m3u8_url
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de l'URL m3u8: {e}")
        return None
    
    def get_best_quality_url(self, m3u8_url):
        try:
            response = requests.get(m3u8_url, headers=self.headers)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            best_resolution = (0, 0)
            best_url = None
            
            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF"):
                    parts = line.split(",")
                    resolution_str = next((part for part in parts if part.startswith("RESOLUTION=")), None)
                    if resolution_str:
                        resolution_str = resolution_str.split("=")[1]
                        width, height = map(int, resolution_str.split("x"))
                        
                        if i + 1 < len(lines) and (width, height) > best_resolution:
                            best_resolution = (width, height)
                            best_url = lines[i + 1]
            
            return best_url
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de la meilleure qualité: {e}")
            return None
    
    def get_segment_urls(self, best_url):
        try:
            response = requests.get(best_url, headers=self.headers)
            response.raise_for_status()
            return [line for line in response.text.splitlines() if line and not line.startswith('#')]
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des URLs des segments: {e}")
            return None
    
    def gestionaire_segmentation(self, segment_urls, segmentation_path):
        return [(url, f"{segmentation_path}seg-{i+1}.ts") for i, url in enumerate(segment_urls)]

    def create_file_list(self, temps_path, segmentation_path):
        file_list_path = os.path.join(temps_path, "file_list.txt")
        ts_files = sorted(
            [f for f in os.listdir(segmentation_path) if f.endswith(".ts")],
            key=lambda x: int(re.search(r'(\d+)', x).group(1)) if re.search(r'(\d+)', x) else float('inf')
        )
        
        self.logger.debug(f"Nombre de fichiers .ts détectés : {len(ts_files)}")
        
        with open(file_list_path, 'w') as file_list:
            for ts_file in ts_files:
                file_list.write(f"file '{os.path.join(segmentation_path, ts_file)}'\n")
        
        self.logger.debug(f"Le fichier de liste a été créé : {file_list_path}")

    def verify_segments(self, segmentation_path):
        try:
            ts_files = [f for f in os.listdir(segmentation_path) if f.endswith(".ts")]
            if not ts_files:
                raise ValueError("Aucun segment .ts trouvé")

            numbers = [int(re.search(r'(\d+)', f).group(1)) for f in ts_files if re.search(r'(\d+)', f)]
            expected_numbers = set(range(1, max(numbers) + 1))
            missing_numbers = expected_numbers - set(numbers)
            
            if missing_numbers:
                raise ValueError(f"Segments manquants : {sorted(missing_numbers)}")

            for ts_file in ts_files:
                if os.path.getsize(os.path.join(segmentation_path, ts_file)) == 0:
                    raise ValueError(f"Le segment {ts_file} est vide")

            self.logger.info(f"Vérification des segments réussie : {len(ts_files)} segments valides")
            return True

        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des segments : {str(e)}")
            return False

    def merge_segments(self, path, temps_path):
        try:
            file_list_path = os.path.join(temps_path, "file_list.txt")
            segmentation_path = os.path.join(temps_path, "segmentation")
            
            if not self.verify_segments(segmentation_path):
                raise ValueError("Les segments ne sont pas valides")
            
            if not os.path.exists(file_list_path):
                raise FileNotFoundError(f"Le fichier de liste {file_list_path} n'existe pas")

            os.makedirs(os.path.dirname(path), exist_ok=True)
            temp_ts_path = os.path.join(temps_path, "temp_output.ts")
            
            # Fusion en .ts
            merge_command = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", file_list_path,
                "-c", "copy",
                "-fflags", "+genpts+igndts",
                "-vsync", "0",
                "-max_interleave_delta", "0",
                "-async", "1",
                "-fflags", "+genpts+igndts+discardcorrupt",
                "-avoid_negative_ts", "make_zero",
                "-y",
                temp_ts_path
            ]
            
            subprocess.run(merge_command, check=True, capture_output=True, text=True)
            
            if not os.path.exists(temp_ts_path) or os.path.getsize(temp_ts_path) == 0:
                raise ValueError("Le fichier temporaire .ts n'a pas été créé correctement")

            # Conversion en .mp4
            convert_command = [
                "ffmpeg",
                "-i", temp_ts_path,
                "-c", "copy",
                "-movflags", "+faststart",
                "-y",
                path
            ]
            
            subprocess.run(convert_command, check=True, capture_output=True, text=True)
            
            # Nettoyage
            if os.path.exists(temp_ts_path):
                os.remove(temp_ts_path)
            
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                raise ValueError("Le fichier de sortie n'a pas été créé correctement")
                
            self.logger.info("Les segments ont été fusionnés avec succès")
            self.status = True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur lors de la fusion des segments: {e.stderr}")
            self.status = False
            raise
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la fusion des segments: {str(e)}")
            self.status = False
            raise