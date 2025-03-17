import json
from datetime import datetime
import pytz
import logging

class build_url:
    def __init__(self, anime_json):
        self.anime_json = anime_json
        self.france_time = self.get_france_time()
        self.logger = logging.getLogger("Anime-sama")
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
                self.logger.info(f"Contenu du fichier : {data}")

            anime_info = []
            for entry in data:
                if not isinstance(entry, dict):
                    self.logger.warning(f"Format invalide pour l'entrée : {entry}")
                    continue

                day = None
                series = []
                
                for key, value in entry.items():
                    if key == "day":
                        day = value
                    elif key == "series":
                        series = value

                if day is None or not series:
                    self.logger.warning(f"Entrée invalide, jour ou séries manquants : {entry}")
                    continue

                if day == self.france_time or day in ["no_day", "download_all"]:
                    for series_info in series:
                        name = series_info.get('name')
                        if name == "none":
                            continue
                        season = series_info.get('season')
                        if season == "none":
                            continue
                        langage = series_info.get('langage')
                        if langage == "none":
                            continue
                        url = f"https://anime-sama.fr/catalogue/{name}/saison{season}/{langage}/"
                        anime_info.append((url, name, season, langage))
                        self.logger.info(f"Ajout de l'anime : {name} saison {season} en {langage}")

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
