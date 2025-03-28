import requests
import json
from datetime import datetime
import pytz

from ...sys.logger import universal_logger

class build_url:
    def __init__(self, anime_json):
        self.anime_json = anime_json
        self.france_time = self.get_france_time()
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        self.anime_info = self.execute()
    
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
    
    def execute(self):
        try:
            self.logger.info(f"Tentative de lecture du fichier {self.anime_json}")
            with open(self.anime_json, 'r') as file:
                data = json.load(file)

            anime_info = []
            for entry in data:
                # Vérifier si l'entrée a un format valide
                if not isinstance(entry, dict):
                    continue

                if "anime_sama" not in entry:
                    continue

                anime_sama_data = entry["anime_sama"]
                if not isinstance(anime_sama_data, list):
                    self.logger.warning(f"Format invalide pour anime_sama_data : {anime_sama_data}")
                    continue

                for day_entry in anime_sama_data:
                    if not isinstance(day_entry, dict):
                        self.logger.warning(f"Format invalide pour day_entry : {day_entry}")
                        continue

                    day = day_entry.get("day")
                    series = day_entry.get("series", [])

                    if not isinstance(series, list):
                        self.logger.warning(f"Format invalide pour series : {series}")
                        continue

                    if day is None:
                        self.logger.warning(f"Entrée invalide, jour manquant : {day_entry}")
                        continue

                    if day == self.france_time or day in ["no_day", "single_download"]:
                        for series_info in series:
                            if not isinstance(series_info, dict):
                                self.logger.warning(f"Format invalide pour series_info : {series_info}")
                                continue

                            name = series_info.get('name')
                            season = series_info.get('season')
                            langage = series_info.get('langage')

                            if not all([name, season, langage]):
                                continue

                            url = f"https://anime-sama.fr/catalogue/{name}/saison{season}/{langage}/episodes.js"
                            anime_info.append((url, name, season, langage))
                            self.logger.debug(f"Ajout de l'anime : {name} saison {season} en {langage}")

            if not anime_info:
                self.logger.warning("Aucun anime trouvé pour aujourd'hui")
            return anime_info

        except FileNotFoundError:
            self.logger.error(f"Fichier {self.anime_json} non trouvé.")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON pour {self.anime_json}: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la lecture de {self.anime_json}: {str(e)}")
            return []
    
def find_episode(anime_name, anime_url, episode_js):
    logger = universal_logger(name=f"Anime-sama - {anime_name}", log_file="anime-sama.log")
    try:
        response = requests.get(anime_url, stream=True)
        response.raise_for_status()
            
        if response.status_code == 200:
            with open(episode_js, 'wb') as file:
                file.write(response.content)
            return True 
        else:
            logger.warning(f"url not work")
            return False    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion : {e}")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête : {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur : {e}")
        return False