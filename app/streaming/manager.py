import os
import json
from configparser import ConfigParser
import re
import pytz
import requests
import time
from datetime import datetime

from ..sys import universal_logger, FolderConfig, EnvConfig
from ..sys.database import anime_data_database
from .api import anime_sama_api, franime_api


class function:
    def __init__(self):
        self.logger = universal_logger(name="Stream Manager - Functions", log_file="sys.log")

    def try_flaresolver(self):
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
        flaresolver_port = config.get("flaresolver", "port", fallback="8191")
        try:
            response = requests.get(f"http://{flaresolver_host}:{flaresolver_port}/health")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Flaresolver est pas accessible: {flaresolver_host}:{flaresolver_port} - {e}")
            return False

    def get_path(self, anime_langage, anime_season, anime_name, franime=False):
        plex_path_json = FolderConfig.find_path(file_name="plex_path.json")
        with open(plex_path_json, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        path_entries = [item for item in data if isinstance(item, dict) and 'path' in item and 'language' in item]

        found_paths = []
        for entry in path_entries:
            if anime_langage in entry['language']:
                found_paths.append(entry['path'])

        if len(found_paths) > 1:
            self.logger.warning(f"Plusieurs dossiers trouvés avec le langage '{anime_langage}'. Utilisation du premier dossier: {found_paths[0]}")
            folder_name = found_paths[0]
        elif len(found_paths) == 1:
            folder_name = found_paths[0]
        else:
            folder_name = None

        if folder_name is None:
            self.logger.warning(f"Aucun dossier trouvé avec le langage '{anime_langage}'")
            return None

        plex_path = EnvConfig.get_env("plex_path")
        download_path = FolderConfig.find_path(folder_name="download")

        path_name = os.path.join(plex_path, folder_name)
        season_name = f"season {anime_season}"
        path_list = (folder_name, anime_name, season_name)
        if franime == False:
            episode_js = f"{download_path}/episode/{anime_name}-s{anime_season}-episode.js"
        else:
            episode_js = f"{download_path}/episode/{anime_name}-s{anime_season}-episode.json"

        return path_name, path_list, episode_js, season_name, folder_name

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
        self.logger.debug(f"France time: {jours_semaine[current_time.weekday()]}")
        return jours_semaine[current_time.weekday()]

    def timer(self):
        timer_logger = universal_logger(name="Timer", log_file="sys.log")
        def format_time(seconds):
            hours, remainder = divmod(seconds, 3600)
            mins, secs = divmod(remainder, 60)
            return f'{hours:02d}:{mins:02d}:{secs:02d}'

        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        seconds = int(config.get("settings", "timer", fallback="3600"))

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

    def get_anime(self, planning=False):
        try:
            anime_json = FolderConfig.find_path(file_name="anime.json")
            france_time = self.get_france_time()
            with open(anime_json, 'r') as file:
                data = json.load(file)

                anime_sama_list = []
                franime_list = []

                def add_anime_to_list(anime, planning=False, day=None):
                    name = anime["name"]
                    season = anime["season"]
                    langage = anime["langage"]
                    file_name = anime["file_name"]
                    jours_mapping = {"lundi": "0", "mardi": "1", "mercredi": "2", "jeudi": "3", "vendredi": "4", "samedi": "5", "dimanche": "6", "no_day": "7", "single_download": "8"}
                    if anime["streaming"] == "anime-sama":
                        if planning == False:
                            anime_sama_list.append((name, season, langage, file_name))
                        else:
                            day = jours_mapping[day]
                            anime_sama_list.append((name, season, langage, day))
                    elif anime["streaming"] == "franime":
                        if planning == False:
                            franime_list.append((name, season, langage, file_name))
                        else:
                            day = jours_mapping[day]
                            franime_list.append((name, season, langage, day))


                for entry in data:
                    if planning == False:
                        if "auto_download" in entry:
                            # Récupère les animes du jour actuel
                            if france_time in entry["auto_download"]:
                                for anime in entry["auto_download"][france_time]:
                                    add_anime_to_list(anime, planning)
                    else:
                        for day in entry["auto_download"]:
                            for anime in entry["auto_download"][day]:
                                add_anime_to_list(anime, planning, day)
                    # Ajoute les animes de no_day
                    if "no_day" in entry["auto_download"]:
                        for anime in entry["auto_download"]["no_day"]:
                            add_anime_to_list(anime, planning, "no_day")

                    # Ajoute les single_download
                    if "single_download" in entry:
                        for anime in entry["single_download"]:
                            add_anime_to_list(anime, planning, "single_download")

                return anime_sama_list, franime_list
        except FileNotFoundError:
            self.logger.error(f"Fichier {anime_json} non trouvé.")
            return [], []
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON pour {anime_json}: {str(e)}")
            return [], []
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de la lecture de {anime_json}: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return [], []

    class planning_scan:
        def __init__(self):
            self.logger = universal_logger(name="Planning Scan", log_file="sys.log")
            self.function = function()
            self.planning_status = {
                "status": "idle",
                "started_at": None,
                "completed_at": None,
                "error": None
            }

        def get_status(self):
            return self.planning_status

        def set_status(self, status, started_at=None, completed_at=None, error=None):
            """Met à jour le statut du scan du planning et le sauvegarde dans le fichier"""
            self.planning_status["status"] = status
            if started_at:
                self.planning_status["started_at"] = started_at
            if completed_at:
                self.planning_status["completed_at"] = completed_at
            if error:
                self.planning_status["error"] = error
            if status == "idle":
                self.planning_status["started_at"] = None
                self.planning_status["completed_at"] = None
                self.planning_status["error"] = None

            # Sauvegarder le statut immédiatement dans le fichier
            try:
                folder_path = FolderConfig.find_path(file_name="planning_scan_data.json")
                if folder_path.exists():
                    with open(folder_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    data["status"] = dict(self.planning_status)
                    with open(folder_path, 'w', encoding='utf-8') as file:
                        json.dump(data, file, indent=4, ensure_ascii=False)
            except Exception as e:
                self.logger.warning(f"Impossible de sauvegarder le statut: {e}")

        def save_planning_data(self, anime_sama_final_list, franime_final_list):
            folder_path = FolderConfig.find_path(file_name="planning_scan_data.json")
            data = []
            if anime_sama_final_list:
                data.extend(list(anime_sama_final_list))
            if franime_final_list:
                data.extend(list(franime_final_list))
            scan_data = {
                "results": data,
                "status": dict(self.planning_status),
                "total": len(data)
            }
            with open(folder_path, 'w', encoding='utf-8') as file:
                json.dump(scan_data, file, indent=4, ensure_ascii=False)


        class anime_sama:
            def __init__(self, anime_sama_list, anime_sama_planning):
                self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
                self.anime_sama_list = anime_sama_list
                self.anime_sama_planning = anime_sama_planning
                self.anime_final_list = []

            def run(self):
                self.build_url()

            def build_url(self):
                self.url_list = []
                for anime in self.anime_sama_list:
                    name = anime[0]
                    anime_sama_api.get_anime_details(name) #cache l'anime dans anime_details.json
                    season = anime[1]
                    langage = anime[2]
                    day = anime[3]

                    config_path = FolderConfig.find_path(file_name="config.conf")
                    config = ConfigParser(allow_no_value=True)
                    config.read(config_path, encoding='utf-8')
                    base_url = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")

                    url = f"{base_url}/catalogue/{name}/saison{season}/{langage}/"
                    json = {"name": name, "season": season, "langage": langage, "day": day, "url": url}

                    self.url_list.append(json)
                self.logger.debug(f"url_list: {self.url_list}")
                self.compare_planning()

            def compare_planning(self):
                self.planning_list = []

                for anime_item in self.url_list:  # anime_sama_url_list est une liste de dict
                    name = anime_item["name"]
                    day = anime_item["day"]
                    season = anime_item["season"]
                    langage = anime_item["langage"]
                    url = anime_item["url"]

                    # Jour 8 (single_download) n'existe pas dans le planning
                    if day == "8":
                        json_result = {
                            "name": name,
                            "season": season,
                            "langage": langage,
                            "url": url,
                            "found": False,
                            "anime_day": day,
                            "planning_day": None
                        }
                    # Jours 0-7 : chercher l'URL dans tous les jours du planning
                    elif day in ["0", "1", "2", "3", "4", "5", "6", "7"]:
                        found = False
                        planning_day_found = None

                        # Chercher l'URL dans tous les jours du planning (0-7)
                        for planning_day, planning_urls in self.anime_sama_planning.items():
                            if url in planning_urls:
                                found = True
                                planning_day_found = planning_day
                                break  # Trouvé, pas besoin de continuer

                        json_result = {
                            "name": name,
                            "season": season,
                            "langage": langage,
                            "url": url,
                            "found": found,
                            "anime_day": day,
                            "planning_day": planning_day_found
                        }
                    else:
                        # Jour invalide
                        json_result = {
                            "name": name,
                            "season": season,
                            "langage": langage,
                            "url": url,
                            "found": False,
                            "anime_day": day,
                            "planning_day": None
                        }
                    self.planning_list.append(json_result)

                self.logger.debug(f"planning_list: {self.planning_list}")
                self.finalize_scan()

            def finalize_scan(self):
                for anime_item in self.planning_list:
                    name = anime_item["name"]
                    season = anime_item["season"]
                    langage = anime_item["langage"]
                    url = anime_item["url"]
                    found = anime_item["found"]
                    anime_day = anime_item["anime_day"]
                    planning_day = anime_item["planning_day"]

                    if found == True:
                        if anime_day == planning_day:
                            STATUS = "0"
                        else:
                            STATUS = "1"
                    elif anime_day == "8":
                        STATUS = "0"
                    else:
                        STATUS = "3"
                    json = {"type": "anime-sama", "name": name, "season": season, "langage": langage, "url": url, "found": found, "anime_day": anime_day, "planning_day": planning_day, "status": STATUS}
                    self.anime_final_list.append(json)
                self.logger.debug(f"anime_list_json: {self.anime_final_list}")

        class franime:
            def __init__(self, franime_list, franime_planning):
                self.logger = universal_logger(name="Franime", log_file="franime.log")
                self.franime_list = franime_list
                self.franime_planning = franime_planning
                self.anime_final_list = []

            def run(self):
                self.compare_planning()

            def compare_planning(self):
                self.planning_list = []

                # Mapping des langages : anime.json -> planning franime
                # "vostfr" -> "vo", "vf" -> "vf", etc.
                langage_mapping = {
                    "vostfr": "vo",
                    "vf": "vf",
                    "vo": "vo"
                }

                for anime_item in self.franime_list:
                    id_anime = anime_item[0]  # id_anime (name dans la liste)
                    franime_api.get_anime_details(id_anime) #cache l'anime dans anime_details.json
                    season = anime_item[1]
                    langage = anime_item[2]
                    day = anime_item[3]

                    # Normaliser le langage pour la comparaison avec le planning
                    langage_normalized = langage_mapping.get(langage, langage)

                    # Jour 8 (single_download) n'existe pas dans le planning
                    if day == "8":
                        json_result = {
                            "id_anime": id_anime,
                            "season": season,
                            "langage": langage,
                            "found": False,
                            "anime_day": day,
                            "planning_day": None
                        }
                    # Jours 0-6 : chercher dans le planning (ignorer jour 7 car toujours vide)
                    elif day in ["0", "1", "2", "3", "4", "5", "6"]:
                        found = False
                        planning_day_found = None

                        # Chercher dans tous les jours du planning (0-6, ignorer 7)
                        for planning_day in ["0", "1", "2", "3", "4", "5", "6"]:
                            if planning_day in self.franime_planning:
                                for planning_anime in self.franime_planning[planning_day]:
                                    # Convertir id_anime en int pour la comparaison
                                    planning_id = planning_anime.get("id_anime")
                                    # Gérer le cas où id_anime peut être int ou string
                                    try:
                                        planning_id_int = int(planning_id) if planning_id is not None else None
                                    except (ValueError, TypeError):
                                        planning_id_int = planning_id

                                    # Comparer id_anime, saison et lang (utiliser langage_normalized)
                                    if (planning_id_int == int(id_anime) and
                                        str(planning_anime.get("saison")) == str(season) and
                                        planning_anime.get("lang") == langage_normalized):
                                        found = True
                                        planning_day_found = planning_day
                                        self.logger.debug(f"Anime {id_anime} trouvé dans le planning au jour {planning_day}")
                                        break
                                if found:
                                    break

                        json_result = {
                            "id_anime": id_anime,
                            "season": season,
                            "langage": langage,
                            "found": found,
                            "anime_day": day,
                            "planning_day": planning_day_found
                        }
                    else:
                        # Jour invalide
                        json_result = {
                            "id_anime": id_anime,
                            "season": season,
                            "langage": langage,
                            "found": False,
                            "anime_day": day,
                            "planning_day": None
                        }
                    self.planning_list.append(json_result)

                self.logger.debug(f"planning_list: {self.planning_list}")
                self.finalize_scan()

            def finalize_scan(self):
                for anime_item in self.planning_list:
                    id_anime = anime_item["id_anime"]
                    season = anime_item["season"]
                    langage = anime_item["langage"]
                    found = anime_item["found"]
                    anime_day = anime_item["anime_day"]
                    planning_day = anime_item["planning_day"]
                    config_path = FolderConfig.find_path(file_name="config.conf")
                    config = ConfigParser(allow_no_value=True)
                    config.read(config_path, encoding='utf-8')
                    base_url = config.get("franime", "base_url", fallback="https://franime.fr")
                    url = f"{base_url}/anime/Plex_anime_downloader?s={season}&ep=&lang={langage if langage == 'vostfr' else 'vo' if langage == 'vf' else langage}&anime_id={id_anime}"

                    if found == True:
                        if anime_day == planning_day:
                            STATUS = "0"
                        else:
                            STATUS = "1"
                    elif anime_day == "8":
                        STATUS = "0"
                    else:
                        STATUS = "3"
                    json = {"type": "franime", "id_anime": id_anime, "season": season, "langage": langage, "url": url, "found": found, "anime_day": anime_day, "planning_day": planning_day, "status": STATUS}
                    self.anime_final_list.append(json)
                self.logger.debug(f"anime_list_json: {self.anime_final_list}")

        def run(self):
            try:
                current_status = self.get_status()
                if current_status.get("status") == "running":
                    self.logger.debug("Un scan des planning est déjà en cours, on skip")
                    return
                self.logger.info("Démarrage du scan des planning")

                self.set_status("running", started_at=datetime.now().isoformat())

                anime_sama_planning = anime_sama_api.get_panning()
                franime_planning = franime_api.get_panning()

                anime_sama_list, franime_list = self.function.get_anime(planning=True)

                AS_scan = self.anime_sama(anime_sama_list, anime_sama_planning)
                AS_scan.run()

                FR_scan = self.franime(franime_list, franime_planning)
                FR_scan.run()

                self.set_status("completed", completed_at=datetime.now().isoformat())
                self.save_planning_data(AS_scan.anime_final_list, FR_scan.anime_final_list)
                self.logger.info("Scan des planning terminé")

            except Exception as e:
                self.logger.error(f"Erreur lors du scan des planning: {e}")
                self.set_status("error", error=str(e))
                return

class stream_manager:
    def __init__(self, queue):
        self.logger = universal_logger(name="Stream Manager", log_file="sys.log")
        self.function = function()
        self.queue = queue

        self.run()

    def run(self):
        while True:
            config_path = FolderConfig.find_path(file_name="config.conf")
            config = ConfigParser(allow_no_value=True)
            config.read(config_path, encoding='utf-8')

            flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
            if flaresolver_use == "true":
                if self.function.try_flaresolver() == False:
                    self.logger.error("Flaresolver est pas accessible, on skip")
                    flaresolver_use = "false"
            else:
                self.logger.info("Flaresolver est désactivé, on skip")
                flaresolver_use = "false"

            planning_scan = self.function.planning_scan()
            planning_scan.run()

            anime_sama_list, franime_list = self.function.get_anime(planning=False)

            anime_sama_scan = config.get("scan-option", "anime-sama", fallback="False")
            franime_scan = config.get("scan-option", "franime", fallback="False")

            if anime_sama_scan == "True":
                anime_sama(anime_sama_list, self.queue)

            if flaresolver_use == "true":
                if franime_scan == "True":
                    franime(franime_list, self.queue)

            self.function.timer()

class anime_sama:
    def __init__(self, anime_sama_list, queue):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")

        config_path = FolderConfig.find_path(file_name="config.conf")
        self.download_path = FolderConfig.find_path(folder_name="download")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')

        self.anime_sama_base_url = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        self.anime_sama_auto_delete = config.get("anime_sama", "auto_delete", fallback="true")
        self.flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")

        self.function = function()
        self.anime_sama_list = anime_sama_list
        self.queue = queue

        self.run()

    def find_part_season(self, name, season, langage):
        url_list = []
        part_season_pattern = r'^\d+-\d+$'
        if re.match(part_season_pattern, str(season)):
            # Extraire le début et la fin
            season_parts = season.split('-')
            season_base = int(season_parts[0])  # Premier nombre (toujours utilisé comme base)
            nombre_parts = int(season_parts[1])  # Deuxième nombre (nombre de parts à créer)

            # Créer une liste d'URLs numérotées (1, 2, 3, 4, 5, etc.)
            # Exemple: 1-3 → base=1, nombre_parts=3 → génère: saison1, saison1-2, saison1-3
            # Exemple: 3-2 → base=3, nombre_parts=2 → génère: saison3, saison3-2
            for current_season in range(1, nombre_parts + 1):
                if current_season == 1:
                    # Si c'est la première itération, utiliser juste saison{base} (sans -1)
                    url = f"{self.anime_sama_base_url}/catalogue/{name}/saison{season_base}/{langage}/episodes.js"
                else:
                    # Sinon, utiliser saison{base}-{current_season}
                    url = f"{self.anime_sama_base_url}/catalogue/{name}/saison{season_base}-{current_season}/{langage}/episodes.js"
                # Ajouter à la liste avec un numéro (1, 2, 3, etc.)
                url_list.append(url)
            return url_list

    def run(self):
        for anime in self.anime_sama_list:
            name = anime[0]
            season = anime[1]
            langage = anime[2]
            file_name = anime[3]
            if file_name == "none":
                file_name = name
            self.logger.info(f"traitement de {file_name} - s{season} - {langage}")

            path_result = self.function.get_path(langage, season, file_name)
            if path_result is None:
                continue

            path_name, path_list, episode_js, season_name, folder_name = path_result

            url_list = self.find_part_season(name, season, langage)
            if url_list:
                episode_js = []
                for i, (url) in enumerate(url_list):
                    episode_js_part = f"{self.download_path}/episode/{file_name}-s{season}-part{i+1}.js"
                    status = anime_sama_api.get_episode_js(file_name, url, episode_js_part)
                    if status:
                        episode_js.append(episode_js_part)
                    else:
                        self.logger.debug(f"Erreur lors du téléchargement du fichier JS pour {file_name} - {season} - {langage}")
            else:
                url = f"{self.anime_sama_base_url}/catalogue/{file_name}/saison{season}/{langage}/episodes.js"
                status = anime_sama_api.get_episode_js(file_name, url, episode_js)
                if status == False:
                    self.logger.debug(f"Erreur lors du téléchargement du fichier JS pour {file_name} - {season} - {langage}")

            # Utiliser la classe get_anime_episodes_url pour extraire et sauvegarder les épisodes
            anime_sama_api.get_anime_episodes_url(path_list, episode_js)

            db = anime_data_database()
            unistalled_episode = db.get_unistalled_episode(path_list)

            if unistalled_episode:
                for episode_name, episode_url in unistalled_episode:
                    self.logger.info(f"nouveaux episode detecté: {episode_name}")
                    episode_path = f"{path_name}/{file_name}/{season_name}/{episode_name}"
                    path = (episode_path, folder_name, file_name, season_name)
                    self.queue.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_url)
            else:
                self.logger.info(f"Aucun nouvel episode detecté pour {file_name} - s{season} - {langage}")

                # Mettre à jour planning_scan_data.json
                planning_scan_data = FolderConfig.find_path(file_name="planning_scan_data.json")
                with open(planning_scan_data, 'r') as file:
                    planning_data = json.load(file)

                # Chercher et mettre à jour l'item dans results
                item_found = None
                if "results" in planning_data:
                    for item in planning_data["results"]:
                        if item.get("name") == name and item.get("found") == False:
                            item["status"] = "2"
                            item_found = item
                            break

                # Si auto_delete activé, retirer l'item et supprimer de anime.json
                if self.anime_sama_auto_delete == "true" and item_found:
                    self.logger.info(f"Suppression de {file_name} - s{season} - {langage}")
                    planning_data["results"].remove(item_found)
                    planning_data["total"] = len(planning_data["results"])

                    # Retirer de anime.json
                    anime_json = FolderConfig.find_path(file_name="anime.json")
                    with open(anime_json, 'r') as file:
                        anime_data = json.load(file)

                    for entry in anime_data:
                        if "auto_download" in entry:
                            for day in entry["auto_download"]:
                                entry["auto_download"][day] = [a for a in entry["auto_download"][day] if a.get("name") != name]
                        if "single_download" in entry:
                            entry["single_download"] = [a for a in entry["single_download"] if a.get("name") != name]

                    with open(anime_json, 'w') as file:
                        json.dump(anime_data, file, indent=4, ensure_ascii=False)

                    # Sauvegarder planning_scan_data.json
                    with open(planning_scan_data, 'w') as file:
                        json.dump(planning_data, file, indent=4, ensure_ascii=False)


class franime:
    def __init__(self, franime_list, queue):
        self.logger = universal_logger(name="Franime", log_file="franime.log")

        config_path = FolderConfig.find_path(file_name="config.conf")
        self.download_path = FolderConfig.find_path(folder_name="download")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')

        self.franime_base_url = config.get("franime", "base_url", fallback="https://franime.fr")
        self.franime_auto_delete = config.get("franime", "auto_delete", fallback="true")
        self.flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")

        self.function = function()
        self.franime_list = franime_list
        self.queue = queue

        self.timer_on = False
        self.timer_thread = None

        self.run()

    def run(self):
        for anime in self.franime_list:
            name = anime[0]
            season = anime[1]
            langage = anime[2]
            if langage == "vostfr":
                frlang = "vo"
            elif langage == "vf":
                frlang = "vf"
            file_name = anime[3]
            if file_name == "none":
                file_name = name
            self.logger.info(f"traitement de {file_name} - s{season} - {langage}")

            path_result = self.function.get_path(langage, season, file_name, franime=True)
            if path_result is None:
                continue

            path_name, path_list, episode_js, season_name, folder_name = path_result

            franime = franime_api.get_anime_episodes_url(path_list, episode_js, name, season, frlang, self.timer_on, self.timer_thread)
            ban = franime.run()
            if ban:
                break

            db = anime_data_database()
            unistalled_episode = db.get_unistalled_episode(path_list)

            if unistalled_episode:
                for episode_name, episode_url in unistalled_episode:
                    self.logger.info(f"nouveaux episode detecté: {episode_name}")
                    episode_path = f"{path_name}/{file_name}/{season_name}/{episode_name}"
                    path = (episode_path, folder_name, file_name, season_name)
                    self.queue.add_to_queue(episode_name=episode_name, path=path, episode_urls=episode_url)
            else:
                self.logger.info(f"Aucun nouvel episode detecté pour {file_name} - s{season} - {langage}")

                # Mettre à jour planning_scan_data.json
                planning_scan_data = FolderConfig.find_path(file_name="planning_scan_data.json")
                with open(planning_scan_data, 'r') as file:
                    planning_data = json.load(file)

                # Chercher et mettre à jour l'item dans results
                item_found = None
                if "results" in planning_data:
                    for item in planning_data["results"]:
                        if item.get("name") == name and item.get("found") == False:
                            item["status"] = "2"
                            item_found = item
                            break

                # Si auto_delete activé, retirer l'item et supprimer de anime.json
                if self.franime_auto_delete == "true" and item_found:
                    self.logger.info(f"Suppression de {file_name} - s{season} - {langage}")
                    planning_data["results"].remove(item_found)
                    planning_data["total"] = len(planning_data["results"])

                    # Retirer de anime.json
                    anime_json = FolderConfig.find_path(file_name="anime.json")
                    with open(anime_json, 'r') as file:
                        anime_data = json.load(file)

                    for entry in anime_data:
                        if "auto_download" in entry:
                            for day in entry["auto_download"]:
                                entry["auto_download"][day] = [a for a in entry["auto_download"][day] if a.get("name") != name]
                        if "single_download" in entry:
                            entry["single_download"] = [a for a in entry["single_download"] if a.get("name") != name]

                    with open(anime_json, 'w') as file:
                        json.dump(anime_data, file, indent=4, ensure_ascii=False)

                    # Sauvegarder planning_scan_data.json
                    with open(planning_scan_data, 'w') as file:
                        json.dump(planning_data, file, indent=4, ensure_ascii=False)
