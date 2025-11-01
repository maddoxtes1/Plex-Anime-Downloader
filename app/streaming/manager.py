import time
import pytz
from datetime import datetime
import json


from ..sys.logger import sys_logger
from ..sys.logger import universal_logger
from .function import anime_sama #, franime

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
    
    def get_france_time(self):
        paris_tz = pytz.timezone('Europe/Paris')
        current_time = datetime.now(paris_tz)
        jours_semaine = {
            0: "lundi",
            1: "mardi",
            2: "mercredi",
            3: "jeudi",
            4: "vendredi",
            5: "samedi",
            6: "dimanche"
        }
        return jours_semaine[current_time.weekday()]
    
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
    
    def get_anime(self):
        try:
            with open(self.anime_json, 'r') as file:
                data = json.load(file)
                
                anime_sama_list = []
                franime_list = []
                
                def add_anime_to_list(anime):
                    name = anime["name"]
                    season = anime["season"]
                    langage = anime["langage"]
                    file_name = anime["file_name"]
                    if anime["streaming"] == "anime-sama":
                        anime_sama_list.append((name, season, langage, file_name))
                    """elif anime["streaming"] == "franime":
                        franime_list.append((name, season, langage, file_name))
                    """
                
                for entry in data:
                    if "auto_download" in entry:
                        # Récupère les animes du jour actuel
                        if self.france_time in entry["auto_download"]:
                            for anime in entry["auto_download"][self.france_time]:
                                add_anime_to_list(anime)
                        
                        # Ajoute les animes de no_day
                        if "no_day" in entry["auto_download"]:
                            for anime in entry["auto_download"]["no_day"]:
                                add_anime_to_list(anime)
                    
                    # Ajoute les single_download
                    if "single_download" in entry:
                        for anime in entry["single_download"]:
                            add_anime_to_list(anime)
                
                return anime_sama_list, franime_list
        except FileNotFoundError:
            self.logger.error(f"Fichier {self.anime_json} non trouvé.")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON pour {self.anime_json}: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la lecture de {self.anime_json}: {str(e)}")
            return []

    def run(self):
        while True:
            self.france_time = self.get_france_time()
            Anime_Sama, FR_Anime = self.scan_option 

            anime_sama_list, franime_list = self.get_anime()
            print(anime_sama_list)
            print(franime_list)

            if Anime_Sama == True:
                self.logger.info(msg="Anime-Sama scan started")
                log = universal_logger(name="Anime-Sama", log_file="anime-sama.log")
                if anime_sama_list:
                    queue_list = []
                    for anime in anime_sama_list:
                        name, season, langage, file_name = anime
                        url = f"https://anime-sama.org/catalogue/{name}/saison{season}/{langage}/episodes.js"
                        if file_name == "none":
                            file_name = name
                        AS = anime_sama(anime_name=file_name, anime_url=url, anime_season=season, anime_langage=langage, plex_path=self.plex_path, download_path=self.download_path)
                        queue = AS.run()
                        if queue:
                            queue_list.append(queue)
                        else:
                            log.warning(f"{name} n'a pas été trouvé")
                    for queue in queue_list:
                        for episode_name, path, episode_url in queue:
                            self.queue.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_url)
        """    if FR_Anime == True:
                self.logger.info(msg="FRAnime scan started")
                log = universal_logger(name="FRAnime", log_file="franime.log")
                if franime_list:
                    for anime in franime_list:
                        name, season, langage, file_name = anime
                        if file_name == "none":
                            file_name = name
                        FR = franime(anime_name=name, file_name=file_name, anime_season=season, anime_langage=langage, plex_path=self.plex_path, download_path=self.download_path)
                        queue = FR.run()
                        if queue:
                            queue_list.append(queue)
                        else:
                            log.warning(f"{name} n'a pas été trouvé")
                    for queue in queue_list:
                        for episode_name, path, episode_url in queue:
                            self.queue.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_url)
            self.timer(seconds=self.seconds)
        """


