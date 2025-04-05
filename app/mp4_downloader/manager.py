from .scrap import *
from .downloaders import *
from .segmentation import *
from urllib.parse import urlparse
import os
import uuid
import logging
import shutil

class manager:
    def __init__(self, download_path, url, logger=None):
        if logger is None:
            self.logger = logging.getLogger("Download Manager")
        else:
            self.logger = logger
        site = {"video.sibnet.ru": self.sibnet, "sendvid.com": self.sendvid}
        self.download_path = download_path
        self.url = url
        self.status = False

        self.success_path = f"{self.download_path}/success"
        if not os.path.exists(self.success_path):
            os.makedirs(self.success_path, exist_ok=True)
    
        # Génère un UUID basé sur l'URL pour avoir le même nom pour la même URL
        random_name = str(uuid.uuid5(uuid.NAMESPACE_URL, self.url))
        self.temp_name = f"{random_name}"
        self.temp_path = f"{download_path}/{self.temp_name}"
        if not os.path.exists(self.temp_path):
            os.makedirs(self.temp_path, exist_ok=True)
        self.file_name = f"{self.temp_path}/{self.temp_name}.mp4"

    
        parsed_url = urlparse(url)
        base_name = parsed_url.netloc

        if base_name in site:
            status = site[base_name]()
            if status:
                path = self.move_to_success()
                if path == False:
                    self.cleanup()
                else:
                    self.file_name = path
                    self.status = True
                    self.cleanup()
            else:
                self.cleanup()
        else:
            raise ValueError(f"Le site {base_name} n'est pas supporté")
    
    def move_to_success(self):
        try:
            file_name = os.path.basename(self.file_name)
            new_path = os.path.join(self.success_path, file_name)
            shutil.move(self.file_name, new_path)
            return new_path
        except Exception as e:
            self.logger.error(f"Erreur lors du déplacement du fichier: {e}")
            return False

    def cleanup(self):
        try:
            shutil.rmtree(self.temp_path)
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression du dossier temporaire: {e}")
    
    def sibnet(self):
        mp4_url = sibnet_scrap(self.url, self.logger)
        if mp4_url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36", "Referer": f"https://video.sibnet.ru"}
            status = mp4_downloader(headers, mp4_url, self.file_name, self.logger)
            return status
        else:
            return False
    
    def vidmoly(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',"Referer": "https://vidmoly.to/"}
        segmentation_path = f"{self.temp_path}/segmentation/"
        segments_txt = f"{self.temp_path}/segments.txt"
        if not os.path.exists(segmentation_path):
            os.makedirs(segmentation_path)
        segments = vidmoly_scrap(self.url, segmentation_path, self.logger)

        downloader = Segment_Downloader(segments=segments, headers=headers, segments_txt=segments_txt, logger=self.logger)
        downloader.download_segments_in_parallel()
        status = merge_segments(self.file_name, self.temp_path, self.logger)
        return status
    
    def oneupload(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',"Referer": "https://oneupload.net/"}
        segmentation_path = f"{self.temp_path}/segmentation/"
        segments_txt = f"{self.temp_path}/segments.txt"
        if not os.path.exists(segmentation_path):
            os.makedirs(segmentation_path)
        segments = oneupload_scrap(self.url, segmentation_path)

        downloader = Segment_Downloader(segments=segments, headers=headers, segments_txt=segments_txt, logger=self.logger)
        downloader.download_segments_in_parallel()
        status = merge_segments(self.file_name, self.temp_path, self.logger)
        return status

    def sendvid(self):
        mp4_url = sendvid_scrap(self.url, self.logger)
        if mp4_url:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36", "Referer": f"https://sendvid.com"}
            status = mp4_downloader(headers, mp4_url, self.file_name, self.logger)
            return status
        else:
            return False