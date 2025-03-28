import time

from ..sys.logger import sys_logger
from .anime_sama.run import anime_sama_run  
from ..sys.logger import universal_logger

class streaming_manager:
    def __init__(self, queue, download_path, plex_path, anime_json, scan_option, timer):
        self.queue = queue
        self.download_path = download_path
        self.plex_path = plex_path
        self.anime_json = anime_json
        self.scan_option = scan_option
        self.seconds = timer
        self.logger = sys_logger()
        self.run()

    def timer(self, seconds):
        timer_logger = universal_logger(name="Timer", log_file="sys.log")
        def format_time(seconds):
            hours, remainder = divmod(seconds, 3600)
            mins, secs = divmod(remainder, 60)
            return f'{hours:02d}:{mins:02d}:{secs:02d}'

        formatted_time = format_time(self.seconds)
        timer_logger.info(f"Starting timer : {formatted_time}")
        
        counter = 0
        while seconds:
            time.sleep(1)
            seconds -= 1 
            counter += 1
            
            if counter >= 900:
                formatted_time = format_time(seconds)
                timer_logger.info(f"Time remaining : {formatted_time}")
                counter = 0
                
        timer_logger.info("Timer ended")

    def run(self):
        while True:
            anime_sama, anime_fr = self.scan_option 

            if anime_sama == True:
                self.logger.info(msg="Anime-Sama scan started")
                anime_sama_run(queues=self.queue, anime_json=self.anime_json, plex_path=self.plex_path, download_path=self.download_path)
            elif anime_fr == True:
                pass
            self.timer(seconds=self.seconds)
        


