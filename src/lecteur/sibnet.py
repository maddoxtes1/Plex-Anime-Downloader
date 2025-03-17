import requests 
from bs4 import BeautifulSoup
import logging
import urllib3
import re
import os
import time

class sibnet_downloader:
    def __init__(self, logger, path, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36", "Referer": f"https://video.sibnet.ru"}
        self.logger = logger
        self.status = False


        mp4_url = self.extract_mp4_url(url=url)

        if mp4_url:
            self.downloading(headers=headers, url=mp4_url, path=path)

    def extract_mp4_url(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive", "Upgrade-Insecure-Requests": "1"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            scripts = soup.find_all('script', type="text/javascript")
            for script in scripts:
                script_content = script.string
                if script_content:
                    match = re.search(r'player\.src\(\[\{src: "(.*?)"', script_content)
                    if match:
                        video_url = match.group(1)
                        url = f"https://video.sibnet.ru{video_url}"
                        return url
        except Exception as e:
            self.logger.error(f"Erreur pendant l'extrait mp4: {e}")
        
    def downloading(self, headers, url, path):
        try:
            http = urllib3.PoolManager()
            urllib3_logger = logging.getLogger("urllib3")
            urllib3_logger.setLevel(logging.WARNING)
            start_byte = os.path.getsize(path) if os.path.exists(path) else 0
            headers["Range"] = f"bytes={start_byte}-"

            response = http.request('GET', url, headers=headers, preload_content=False)
            if response.status == 200:
                self.logger.info("Téléchargement complet (HTTP 200).")
                start_byte = 0
            elif response.status == 206:
                self.logger.info("Reprise du téléchargement (HTTP 206).")
            elif response.status == 416:
                self.logger.warning("Plage invalide, tentative de téléchargement complet.")
                if os.path.exists(path):
                    os.remove(path)
                self.logger.info(f"Fichier local {path} supprimé.")
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
                    self.logger.warning(f"Le fichier est déjà complet. Aucun téléchargement nécessaire.")
                    self.status = True
                    return
                
            with open(path, "ab") as f:
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
