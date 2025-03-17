import requests 
from bs4 import BeautifulSoup
import logging
import src.function as Function
import re
import concurrent.futures
import aiohttp
import asyncio
import os
import subprocess
import time

class SegmentDownloader:
    def __init__(self, segments, headers):
        self.segments = segments
        self.headers = headers
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
            print(f"Erreur lors du téléchargement du fichier {url}: {e}")
            if retry_count < self.max_retries:
                print(f"Tentative de reprise {retry_count + 1}/{self.max_retries}")
                time.sleep(2 ** retry_count)  # Backoff exponentiel
                return self.download_segment(url, filename, retry_count + 1)
            return False
        except OSError as e:
            print(f"Erreur système lors de l'écriture du fichier {filename}: {e}")
            return False
        except Exception as e:
            print(f"Erreur inattendue lors du téléchargement de {url}: {e}")
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
                    print(f"Erreur lors du téléchargement de {url}: {e}")
                    failed_segments.append((url, filename))

        if failed_segments:
            print(f"{len(failed_segments)} segments ont échoué. Tentative de reprise...")
            for url, filename in failed_segments:
                if not self.download_segment(url, filename):
                    print(f"Échec définitif du téléchargement de {url}")

    async def download_segment_async(self, session, url, filename, retry_count=0):
        try:
            async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                if response.status == 200:
                    # Vérifie l'espace disponible
                    content_length = int(response.headers.get('content-length', 0))
                    if content_length > 0:
                        free_space = os.statvfs(os.path.dirname(filename)).f_bfree * os.statvfs(os.path.dirname(filename)).f_bsize
                        if content_length > free_space:
                            raise OSError(f"Espace disque insuffisant pour {filename}")

                    with open(filename, 'wb') as file:
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            if chunk:
                                file.write(chunk)
                    print(f"Le fichier {filename} a été téléchargé avec succès.")
                    return True
                else:
                    print(f"Erreur lors du téléchargement du fichier {url}. Statut HTTP: {response.status}")
                    if retry_count < self.max_retries:
                        print(f"Tentative de reprise {retry_count + 1}/{self.max_retries}")
                        await asyncio.sleep(2 ** retry_count)
                        return await self.download_segment_async(session, url, filename, retry_count + 1)
                    return False
        except asyncio.TimeoutError:
            print(f"Timeout lors du téléchargement de {url}")
            if retry_count < self.max_retries:
                await asyncio.sleep(2 ** retry_count)
                return await self.download_segment_async(session, url, filename, retry_count + 1)
            return False
        except Exception as e:
            print(f"Erreur lors du téléchargement de {url}: {e}")
            return False

    async def download_segments_in_parallel_async(self):
        failed_segments = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url, filename in self.segments:
                task = asyncio.create_task(self.download_segment_async(session, url, filename))
                tasks.append((task, url, filename))
            
            for task, url, filename in tasks:
                try:
                    success = await task
                    if not success:
                        failed_segments.append((url, filename))
                except Exception as e:
                    print(f"Erreur lors du téléchargement de {url}: {e}")
                    failed_segments.append((url, filename))

        if failed_segments:
            print(f"{len(failed_segments)} segments ont échoué. Tentative de reprise...")
            async with aiohttp.ClientSession() as session:
                for url, filename in failed_segments:
                    if not await self.download_segment_async(session, url, filename):
                        print(f"Échec définitif du téléchargement de {url}")

class oneupload_downloader:
    def __init__(self, logger, download_path, name, path, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3', "Referer": "https://oneupload.net/"}
        self.logger = logger
        self.status = False
        temps_path = f"{download_path}/{name}"
        Function.create_path(path=temps_path)

        m3u8_url = self.get_m3u8_url(url=url, headers=headers)

        best_url = self.get_best_quality_url(m3u8_url=m3u8_url, headers=headers)

        segment_urls = self.get_segment_urls(best_url=best_url, headers=headers)

        segmentation_path = f"{temps_path}/segmentation/"
        Function.create_path(path=segmentation_path)
        segments = self.gestionaire_segmentation(segment_urls=segment_urls, segmentation_path=segmentation_path)

        downloader = SegmentDownloader(segments=segments, headers=headers)
        downloader.download_segments_in_parallel()

        self.create_file_list(temps_path=temps_path, segmentation_path=segmentation_path)
        self.merge_segments(path=path, temps_path=temps_path)


    def get_m3u8_url(self, url, headers):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r'file:"(https?://[^"]+\.m3u8[^"]*)"', script.string)
                    if match:
                        m3u8_url = match.group(1)  # Utilise group(1) pour obtenir uniquement l'URL
                        self.logger.info(msg=f"URL trouvée : {m3u8_url}")
                        return m3u8_url
    
    def get_best_quality_url(self, m3u8_url, headers):
        response = requests.get(m3u8_url, headers=headers)
        if response.status_code != 200:
            self.logger.error(msg=f"Erreur de téléchargement du fichier M3U8. Statut HTTP: {response.status_code}")
            raise Exception(f"Erreur de téléchargement du fichier M3U8. Statut HTTP: {response.status_code}")
            
        lines = response.text.splitlines()
        best_resolution = (0, 0)
        best_url = None
        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF"):
                parts = line.split(",")
                resolution_str = next((part for part in parts if part.startswith("RESOLUTION=")), None)
                if resolution_str:
                    resolution_str = resolution_str.split("=")[1]
                    width, height = map(int, resolution_str.split("x"))
                        
                    index = lines.index(line) + 1
                    if index < len(lines):
                        url = lines[index]
                            
                        if (width, height) > best_resolution:
                            best_resolution = (width, height)
                            best_url = url
        if not best_url:
            self.logger.error(msg="Aucune URL valide trouvée dans le fichier M3U8.")
            raise Exception("Aucune URL valide trouvée dans le fichier M3U8.")
        return best_url
    
    def get_segment_urls(self, best_url, headers):
        response = requests.get(best_url, headers=headers)
        if response.status_code != 200:
            self.logger.error(msg=f"Erreur de téléchargement du fichier M3U8. Statut HTTP: {response.status_code}")
            raise Exception(f"Erreur de téléchargement du fichier M3U8. Statut HTTP: {response.status_code}")


        lines = response.text.splitlines()
        segment_urls = []
        
        for line in lines:
            if line and not line.startswith('#'):
                segment_urls.append(line)

        if not segment_urls:
            self.logger.error(msg="Aucune URL de segment trouvée dans le fichier M3U8.")
            raise Exception("Aucune URL de segment trouvée dans le fichier M3U8.")
        
        return segment_urls
    
    def gestionaire_segmentation(self, segment_urls, segmentation_path):
        number = 1
        segment = []
        for url in segment_urls:
            segment.append((url, f"{segmentation_path}seg-{number}.ts"))
            number += 1
        return segment

    def create_file_list(self, temps_path, segmentation_path):
        file_list_path = os.path.join(temps_path, "file_list.txt")
        
        ts_files = [f for f in os.listdir(segmentation_path) if f.endswith(".ts")]
        
        def extract_number(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else float('inf')
        
        sorted_ts_files = sorted(ts_files, key=extract_number)
        
        self.logger.info(msg=f"Nombre de fichiers .ts détectés : {len(sorted_ts_files)}")
        
        with open(file_list_path, 'w') as file_list:
            for ts_file in sorted_ts_files:
                file_list.write(f"file '{os.path.join(segmentation_path, ts_file)}'\n")
        
        self.logger.info(msg=f"Le fichier de liste a été créé : {file_list_path}")

    def verify_segments(self, segmentation_path):
        """Vérifie que tous les segments sont présents et valides"""
        try:
            ts_files = [f for f in os.listdir(segmentation_path) if f.endswith(".ts")]
            if not ts_files:
                raise ValueError("Aucun segment .ts trouvé")

            # Vérifie que tous les segments sont présents
            numbers = [int(re.search(r'(\d+)', f).group(1)) for f in ts_files if re.search(r'(\d+)', f)]
            expected_numbers = set(range(1, max(numbers) + 1))
            missing_numbers = expected_numbers - set(numbers)
            
            if missing_numbers:
                raise ValueError(f"Segments manquants : {sorted(missing_numbers)}")

            # Vérifie la taille de chaque segment
            for ts_file in ts_files:
                file_path = os.path.join(segmentation_path, ts_file)
                if os.path.getsize(file_path) == 0:
                    raise ValueError(f"Le segment {ts_file} est vide")

            self.logger.info(msg=f"Vérification des segments réussie : {len(ts_files)} segments valides")
            return True

        except Exception as e:
            self.logger.error(msg=f"Erreur lors de la vérification des segments : {str(e)}")
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

            # Première étape : fusionner en .ts avec synchronisation améliorée
            temp_ts_path = os.path.join(temps_path, "temp_output.ts")
            
            # Commande pour fusionner en .ts avec synchronisation améliorée
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
            
            merge_result = subprocess.run(
                merge_command,
                check=True,
                capture_output=True,
                text=True
            )
            
            if not os.path.exists(temp_ts_path):
                raise FileNotFoundError(f"Le fichier temporaire .ts n'a pas été créé")
                
            if os.path.getsize(temp_ts_path) == 0:
                raise ValueError(f"Le fichier temporaire .ts est vide")

            # Deuxième étape : simple conversion de .ts vers .mp4
            convert_command = [
                "ffmpeg",
                "-i", temp_ts_path,
                "-c", "copy",  # Copie directe sans réencodage
                "-movflags", "+faststart",  # Pour la lecture immédiate
                "-y",
                path
            ]
            
            convert_result = subprocess.run(
                convert_command,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Nettoyage du fichier temporaire
            if os.path.exists(temp_ts_path):
                os.remove(temp_ts_path)
            
            if not os.path.exists(path):
                raise FileNotFoundError(f"Le fichier de sortie {path} n'a pas été créé")
                
            if os.path.getsize(path) == 0:
                raise ValueError(f"Le fichier de sortie {path} est vide")
                
            self.logger.info(msg=f"Les segments ont été fusionnés avec succès en {path}")
            self.status = True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(msg=f"Erreur lors de la fusion des segments: {e.stderr}")
            self.status = False
            raise
        except Exception as e:
            self.logger.error(msg=f"Erreur inattendue lors de la fusion des segments: {str(e)}")
            self.status = False
            raise