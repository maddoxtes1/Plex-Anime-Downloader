import time
import pytz
from datetime import datetime
import json
import re
from configparser import ConfigParser

from ..sys import FolderConfig, EnvConfig, universal_logger
from .function import anime_sama #, franime

class streaming_manager:
    def __init__(self, queue):
        self.queue = queue
        self.download_path = FolderConfig.find_path(folder_name="download")
        self.plex_path = EnvConfig.get_env("plex_path")
        self.anime_json = FolderConfig.find_path(file_name="anime.json")

        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')

        self.anime_sama = config.get("scan-option", "anime-sama", fallback="True").lower() == "true"
        self.franime = config.get("scan-option", "franime", fallback="False").lower() == "true"
        self.as_baseurl = config.get("scan-option", "as_Baseurl", fallback="https://anime-sama.tv")
        
        self.seconds = int(config.get("settings", "timer", fallback="3600"))
        self.logger = universal_logger("System", "sys.log")
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

        formatted_time = format_time(seconds)
        timer_logger.info(f"Starting timer : {formatted_time}")
        
        counter = 0
        remaining_seconds = seconds
        while remaining_seconds > 0:
            time.sleep(1)
            remaining_seconds -= 1 
            counter += 1
            
            if counter >= 900:
                formatted_time = format_time(remaining_seconds)
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
                
                return anime_sama_list,franime_list
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

            anime_sama_list, franime_list = self.get_anime()
            franime_list = False # remove this line when franime is ready

            if self.anime_sama == True:
                self.logger.info(msg="Anime-Sama scan started")
                log = universal_logger(name="Anime-Sama", log_file="anime-sama.log")
                if anime_sama_list:
                    queue_list = []
                    for anime in anime_sama_list:
                        name, season, langage, file_name = anime
                        if file_name == "none":
                            file_name = name
                        
                        # Vérifier si season est au format "x-y" (ex: "1-2", "1-3", "3-2")
                        part_season_pattern = r'^\d+-\d+$'
                        if re.match(part_season_pattern, str(season)):
                            # Extraire le début et la fin
                            season_parts = season.split('-')
                            season_base = int(season_parts[0])  # Premier nombre (toujours utilisé comme base)
                            nombre_parts = int(season_parts[1])  # Deuxième nombre (nombre de parts à créer)
                            
                            # Créer une liste d'URLs numérotées (1, 2, 3, 4, 5, etc.)
                            # Exemple: 1-3 → base=1, nombre_parts=3 → génère: saison1, saison1-2, saison1-3
                            # Exemple: 3-2 → base=3, nombre_parts=2 → génère: saison3, saison3-2
                            url_list = []
                            for current_season in range(1, nombre_parts + 1):
                                if current_season == 1:
                                    # Si c'est la première itération, utiliser juste saison{base} (sans -1)
                                    url = f"{self.as_baseurl}/catalogue/{name}/saison{season_base}/{langage}/episodes.js"
                                    season_for_object = season_base
                                else:
                                    # Sinon, utiliser saison{base}-{current_season}
                                    url = f"{self.as_baseurl}/catalogue/{name}/saison{season_base}-{current_season}/{langage}/episodes.js"
                                    season_for_object = f"{season_base}-{current_season}"
                                
                                # Ajouter à la liste avec un numéro (1, 2, 3, etc.)
                                url_list.append(url)
                            
                            # Traiter avec la liste d'URLs (utiliser season_base comme season_for_object)
                            AS = anime_sama(anime_name=file_name, anime_url=url_list, anime_season=season_base, anime_langage=langage, plex_path=self.plex_path, download_path=self.download_path)
                            queue = AS.run()
                            if queue:
                                queue_list.append(queue)
                            else:
                                log.info(f"{name} tous les épisodes sont déjà installés ou aucun nouveau épisode disponible")
                        else:
                            # Si ce n'est pas un format de plage, traiter normalement
                            url = f"{self.as_baseurl}/catalogue/{name}/saison{season}/{langage}/episodes.js"
                            AS = anime_sama(anime_name=file_name, anime_url=url, anime_season=season, anime_langage=langage, plex_path=self.plex_path, download_path=self.download_path)
                            queue = AS.run()
                            if queue:
                                queue_list.append(queue)
                            else:
                                log.info(f"{name} tous les épisodes sont déjà installés ou aucun nouveau épisode disponible")
                    for queue in queue_list:
                        for episode_name, path, episode_url in queue:
                            self.queue.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_url)
            self.timer(seconds=self.seconds)
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


