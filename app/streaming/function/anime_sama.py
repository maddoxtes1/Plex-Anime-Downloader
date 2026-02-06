import os
import re
import copy

from ...sys import universal_logger, FolderConfig
from ..api import find_episode, extract_link, extract_all_part_episode, get_planning_anime_urls, extract_anime_info
from ...sys.database import database
import json
from configparser import ConfigParser

class anime_sama:
    def __init__(self, anime_name, anime_url, anime_season, anime_langage, plex_path, download_path):
        self.logger = universal_logger(name=f"Anime-sama - {anime_name} s{anime_season}", log_file="anime-sama.log")
        self.anime_name = anime_name
        self.anime_url = anime_url
        self.anime_season = anime_season
        self.anime_langage = anime_langage
        self.plex_path = plex_path
        self.download_path = download_path


    def get_path(self):
        plex_path_json = FolderConfig.find_path(file_name="plex_path.json")
        with open(plex_path_json, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        path_entries = [item for item in data if isinstance(item, dict) and 'path' in item and 'language' in item]

        found_paths = []
        for entry in path_entries:
            if self.anime_langage in entry['language']:
                found_paths.append(entry['path'])

        if len(found_paths) > 1:
            self.logger.warning(f"Plusieurs dossiers trouvés avec le langage '{self.anime_langage}'. Utilisation du premier dossier: {found_paths[0]}")
            folder_name = found_paths[0]
        elif len(found_paths) == 1:
            folder_name = found_paths[0]
        else:
            folder_name = None

        if folder_name is None:
            self.logger.warning(f"Aucun dossier trouvé avec le langage '{self.anime_langage}'")
            return None
        
        path_name = os.path.join(self.plex_path, folder_name)
        season_name = f"season {self.anime_season}"
        path_list = (folder_name, self.anime_name, season_name)
        episode_js = f"{self.download_path}/episode/{self.anime_name}-s{self.anime_season}-episode.js"

        return path_name, path_list, episode_js, season_name, folder_name

    def run(self):
        path_result = self.get_path()
        if path_result is None:
            return
        
        path_name, path_list, episode_js, season_name, folder_name = path_result
        
        # Vérifier si anime_url est une liste
        if isinstance(self.anime_url, list):
            # Traiter chaque URL de la liste
            episode_js_list = []
            for i, (url) in enumerate(self.anime_url): 
                episode_js_part = f"{self.download_path}/episode/{self.anime_name}-s{self.anime_season}-part{i+1}.js"
                status = find_episode(anime_name=self.anime_name, anime_url=url, episode_js=episode_js_part)
                if status == False:
                    continue
                episode_js_list.append(episode_js_part)
            extract_all_part_episode(path_list=path_list, episode_js_list=episode_js_list)
        else:
            # Traiter l'URL unique
            status = find_episode(anime_name=self.anime_name, anime_url=self.anime_url, episode_js=episode_js)
            if status == False:
                return
            extract_link(path_list=path_list, episode_js=episode_js)

        db = database()
        uninstalled = db.get_unistalled_episode(path_list=path_list)

        queue = []
        if uninstalled:
            for episode_name, episode_url in uninstalled:
                self.logger.info(f"nouveaux episode detecté: {episode_name}")
                episode_path = f"{path_name}/{self.anime_name}/{season_name}/{episode_name}"
                path = (episode_path, folder_name, self.anime_name, season_name)
                queue.append((episode_name, path, episode_url))
        return queue

class anime_sama_planning:
    def __init__(self):
        self.planning = get_planning_anime_urls()
        self.anime_list = []

        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        self.as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        
        # Lire auto_planning depuis la config
        try:
            auto_planning_str = config.get("anime_sama", "auto_planning", fallback="True")
            self.auto_planning = auto_planning_str.lower() in ("true", "1", "yes", "on")
        except Exception:
            self.auto_planning = True  # Par défaut True
        
        # Récupérer les chemins nécessaires pour vérifier les épisodes
        from ...sys import EnvConfig
        self.download_path = FolderConfig.find_path(folder_name="download")
        self.plex_path = EnvConfig.get_env("plex_path")
        
        # Charger le fichier anime.json et stocker son chemin
        self.anime_json_path = FolderConfig.find_path(file_name="anime.json")
        if self.anime_json_path and self.anime_json_path.exists():
            with open(self.anime_json_path, 'r', encoding='utf-8') as f:
                self.anime_json = json.load(f)
        else:
            self.anime_json = []    

    def compare_planning(self, anime_url, anime_day):
        """
        Compare une URL d'anime avec le planning.
        Pour les saisons au format "x-y", vérifie aussi les variantes (ex: saison1 et saison1-2).
        
        Args:
            anime_url: URL de l'anime à comparer (peut être une liste de variantes)
            anime_day: ID du jour attendu (0-6) ou None pour chercher dans tous les jours
        
        Returns:
            dict: {
                "found": bool,        # Si l'anime est trouvé dans le planning
                "anime_day": str,     # Le jour attendu (celui passé en paramètre)
                "day_id": str ou None # Le jour où il a été trouvé (None si pas trouvé)
            }
        """
        # Si anime_url est une liste (variantes), vérifier toutes les variantes
        urls_to_check = anime_url if isinstance(anime_url, list) else [anime_url]
        
        # Si un jour spécifique est fourni, chercher d'abord dans ce jour
        if anime_day is not None:
            if anime_day in self.planning:
                for url_to_check in urls_to_check:
                    for url in self.planning[anime_day]:
                        if url == url_to_check:
                            # Trouvé dans le bon jour
                            return {
                                "found": True,
                                "anime_day": anime_day,
                                "day_id": anime_day
                            }
        
        # Si pas trouvé dans le jour spécifique (ou si anime_day est None),
        # chercher dans tous les autres jours
        for day_id, day_url in self.planning.items():
            # Ignorer le jour déjà vérifié si anime_day était spécifié
            if anime_day is not None and day_id == anime_day:
                continue
            
            for url_to_check in urls_to_check:
                for url in day_url:
                    if url == url_to_check:
                        # Trouvé mais dans un autre jour
                        return {
                            "found": True,
                            "anime_day": anime_day,  # Le jour attendu
                            "day_id": day_id         # Le jour où il a été trouvé
                        }
        
        # Pas trouvé du tout
        return {
            "found": False,
            "anime_day": anime_day,
            "day_id": None
        }
    
    def build_anime_url(self, anime_name, anime_season, anime_langage):
        """
        Construit l'URL de base d'un anime.
        Pour les saisons au format "x-y", retourne l'URL avec la saison complète (ex: saison1-2).
        """
        return f"{self.as_baseurl}/catalogue/{anime_name}/saison{anime_season}/{anime_langage}/"
    
    def build_anime_url_variants(self, anime_name, anime_season, anime_langage):
        """
        Construit toutes les variantes d'URL possibles pour un anime avec saison au format "x-y".
        Par exemple, pour "1-2", retourne ["saison1", "saison1-2"].
        Pour une saison simple, retourne juste [saisonX].
        
        Returns:
            list: Liste des URLs possibles
        """
        # Vérifier si season est au format "x-y"
        part_season_pattern = r'^\d+-\d+$'
        if re.match(part_season_pattern, str(anime_season)):
            season_parts = str(anime_season).split('-')
            season_base = int(season_parts[0])
            nombre_parts = int(season_parts[1])
            
            urls = []
            # Ajouter saison{base}
            urls.append(f"{self.as_baseurl}/catalogue/{anime_name}/saison{season_base}/{anime_langage}/")
            # Ajouter saison{base}-{part} pour chaque part
            for part in range(2, nombre_parts + 1):
                urls.append(f"{self.as_baseurl}/catalogue/{anime_name}/saison{season_base}-{part}/{anime_langage}/")
            return urls
        else:
            # Saison simple
            return [f"{self.as_baseurl}/catalogue/{anime_name}/saison{anime_season}/{anime_langage}/"]
    
    def check_episodes_complete(self, anime_name, anime_season, anime_langage):
        """
        Vérifie si tous les épisodes d'un anime sont installés.
        Télécharge le fichier episodes.js, extrait les épisodes et compare avec la database.
        Gère les saisons au format "x-y" (ex: "1-2", "3-2") en combinant plusieurs fichiers episodes.js.
        
        Args:
            anime_name: Nom de l'anime
            anime_season: Numéro de saison (peut être "1-2", "3-2", etc.)
            anime_langage: Langage (vostfr, vf, etc.)
        
        Returns:
            bool: True si tous les épisodes sont installés, False sinon, None en cas d'erreur
        """
        logger = universal_logger(name="Anime-sama - Planning Compare", log_file="anime-sama.log")
        
        try:
            # Récupérer le path comme dans anime_sama.get_path()
            plex_path_json = FolderConfig.find_path(file_name="plex_path.json")
            if not plex_path_json or not plex_path_json.exists():
                logger.warning(f"Impossible de trouver plex_path.json pour {anime_name} (s{anime_season}, {anime_langage})")
                logger.debug(f"  Chemin cherché: {plex_path_json}")
                return None
            
            with open(plex_path_json, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
            
            path_entries = [item for item in data if isinstance(item, dict) and 'path' in item and 'language' in item]
            
            found_paths = []
            for entry in path_entries:
                if anime_langage in entry['language']:
                    found_paths.append(entry['path'])
            
            if not found_paths:
                logger.warning(f"Aucun dossier trouvé pour le langage '{anime_langage}' pour {anime_name} (s{anime_season})")
                logger.debug(f"  Langages disponibles: {[entry.get('language') for entry in path_entries]}")
                return None
            
            folder_name = found_paths[0]
            path_name = os.path.join(self.plex_path, folder_name)
            
            # Vérifier si season est au format "x-y" (ex: "1-2", "1-3", "3-2")
            part_season_pattern = r'^\d+-\d+$'
            is_part_season = re.match(part_season_pattern, str(anime_season))
            
            if is_part_season:
                # Extraire le début et la fin
                season_parts = str(anime_season).split('-')
                season_base = int(season_parts[0])  # Premier nombre (toujours utilisé comme base)
                nombre_parts = int(season_parts[1])  # Deuxième nombre (nombre de parts à créer)
                
                logger.debug(f"Traitement d'une saison multi-parties pour {anime_name}: {anime_season} (base={season_base}, parts={nombre_parts})")
                
                # Créer une liste d'URLs numérotées (1, 2, 3, 4, 5, etc.)
                # Exemple: 1-2 → base=1, nombre_parts=2 → génère: saison1, saison1-2
                # Exemple: 3-2 → base=3, nombre_parts=2 → génère: saison3, saison3-2
                episode_js_list = []
                for current_season in range(1, nombre_parts + 1):
                    if current_season == 1:
                        # Si c'est la première itération, utiliser juste saison{base} (sans -1)
                        episodes_js_url = f"{self.as_baseurl}/catalogue/{anime_name}/saison{season_base}/{anime_langage}/episodes.js"
                        episode_js_part = f"{self.download_path}/episode/{anime_name}-s{season_base}-part1.js"
                    else:
                        # Sinon, utiliser saison{base}-{current_season}
                        episodes_js_url = f"{self.as_baseurl}/catalogue/{anime_name}/saison{season_base}-{current_season}/{anime_langage}/episodes.js"
                        episode_js_part = f"{self.download_path}/episode/{anime_name}-s{season_base}-part{current_season}.js"
                    
                    logger.debug(f"  Téléchargement part {current_season}: {episodes_js_url}")
                    
                    # Télécharger le fichier episodes.js
                    status = find_episode(anime_name=anime_name, anime_url=episodes_js_url, episode_js=episode_js_part)
                    if not status:
                        logger.warning(f"Impossible de télécharger episodes.js pour {anime_name} (part {current_season})")
                        logger.debug(f"  URL essayée: {episodes_js_url}")
                        # Continuer avec les autres parts même si une échoue
                        continue
                    
                    episode_js_list.append(episode_js_part)
                
                if not episode_js_list:
                    logger.warning(f"Aucun fichier episodes.js téléchargé pour {anime_name} (s{anime_season}, {anime_langage})")
                    return None
                
                # Utiliser season_base pour le path_list (comme dans manager.py)
                season_name = f"season {season_base}"
                path_list = (folder_name, anime_name, season_name)
                
                # Combiner tous les fichiers episodes.js
                extract_all_part_episode(path_list=path_list, episode_js_list=episode_js_list)
            else:
                # Traitement normal pour une saison simple
                season_name = f"season {anime_season}"
                path_list = (folder_name, anime_name, season_name)
                episode_js = f"{self.download_path}/episode/{anime_name}-s{anime_season}-episode.js"
                
                # Construire l'URL du fichier episodes.js
                episodes_js_url = f"{self.as_baseurl}/catalogue/{anime_name}/saison{anime_season}/{anime_langage}/episodes.js"
                
                logger.debug(f"Vérification des épisodes pour {anime_name} (s{anime_season}, {anime_langage})")
                logger.debug(f"  URL: {episodes_js_url}")
                
                # Télécharger le fichier episodes.js
                status = find_episode(anime_name=anime_name, anime_url=episodes_js_url, episode_js=episode_js)
                if not status:
                    logger.warning(f"Impossible de télécharger episodes.js pour {anime_name} (s{anime_season}, {anime_langage})")
                    logger.debug(f"  URL essayée: {episodes_js_url}")
                    return None
                
                # Extraire les épisodes et les ajouter à la database
                extract_link(path_list=path_list, episode_js=episode_js)
            
            # Vérifier dans la database s'il y a des épisodes non installés
            db = database()
            uninstalled = db.get_unistalled_episode(path_list=path_list)
            
            # Si aucun épisode non installé, tous les épisodes sont complets
            episodes_complete = len(uninstalled) == 0
            
            logger.info(f"Anime '{anime_name}' s{anime_season} ({anime_langage}): {len(uninstalled)} épisodes non installés, complets: {episodes_complete}")
            
            return episodes_complete
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des épisodes pour {anime_name} (s{anime_season}, {anime_langage}): {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def run(self):
        """
        Compare tous les animes du fichier anime.json avec le planning.
        Pour chaque anime, construit l'URL et vérifie si elle est dans le planning.
        Sauvegarde le résultat dans self.anime_list avec {name, day_id, bool}.
        """
        logger = universal_logger(name="Anime-sama - Planning Compare", log_file="anime-sama.log")
        
        # Mapping des jours de la semaine vers les IDs
        jours_mapping = {
            "lundi": "0",
            "mardi": "1",
            "mercredi": "2",
            "jeudi": "3",
            "vendredi": "4",
            "samedi": "5",
            "dimanche": "6",
            "no_day": "7",
            "single_download": "8"
    
        }
        
        # Parcourir tous les entrées dans anime_json (c'est une liste)
        total_animes_checked = 0
        skipped_not_anime_sama = 0
        skipped_incomplete = 0
        
        logger.debug(f"Nombre d'entrées dans anime_json: {len(self.anime_json) if isinstance(self.anime_json, list) else 'N/A (pas une liste)'}")
        
        if not isinstance(self.anime_json, list):
            logger.error(f"anime_json n'est pas une liste, type: {type(self.anime_json)}")
            return self.anime_list
        
        for entry_idx, entry in enumerate(self.anime_json):
            logger.debug(f"Traitement de l'entrée {entry_idx + 1}/{len(self.anime_json)}")
            
            if not isinstance(entry, dict):
                logger.warning(f"Entrée {entry_idx} n'est pas un dictionnaire, ignorée")
                continue
            
            # Traiter single_download (en premier, car c'est une liste directe)
            if "single_download" in entry:
                single_download_list = entry["single_download"]
                logger.info(f"Traitement de {len(single_download_list) if isinstance(single_download_list, list) else 0} animes single_download")
                
                if not isinstance(single_download_list, list):
                    logger.warning(f"  single_download n'est pas une liste dans l'entrée {entry_idx}")
                else:
                    day_id = "8"  # single_download = jour 8
                    
                    for anime in single_download_list:
                        total_animes_checked += 1
                        
                        # Vérifier que c'est un anime anime-sama
                        streaming = anime.get("streaming")
                        if streaming != "anime-sama":
                            skipped_not_anime_sama += 1
                            logger.debug(f"Anime ignoré (streaming='{streaming}' au lieu de 'anime-sama'): {anime.get('name', 'N/A')}")
                            continue
                        
                        name = anime.get("name")
                        season = anime.get("season")
                        langage = anime.get("langage")
                        
                        if not name or not season or not langage:
                            skipped_incomplete += 1
                            logger.warning(f"Anime incomplet dans single_download: {anime}")
                            continue
                        
                        # Pour single_download, on ne cherche pas dans le planning
                        # On vérifie juste si l'anime existe et si tous les épisodes sont téléchargés
                        anime_info = extract_anime_info(name)
                        
                        if anime_info is None:
                            # Anime non trouvé sur anime-sama
                            anime_entry = {
                                "name": name,
                                "season": season,
                                "langage": langage,
                                "found": False,
                                "anime_day": day_id,
                                "day_id": None,
                                "episodes_complete": None,
                                "status": "red"  # Pas trouvé
                            }
                            logger.debug(f"Anime '{name}' (single_download) - Non trouvé sur anime-sama")
                        else:
                            # Anime trouvé, vérifier les épisodes
                            episodes_complete = self.check_episodes_complete(name, season, langage)
                            
                            if episodes_complete is None:
                                # Impossible de vérifier les épisodes
                                anime_entry = {
                                    "name": name,
                                    "season": season,
                                    "langage": langage,
                                    "found": True,  # Trouvé sur anime-sama
                                    "anime_day": day_id,
                                    "day_id": None,
                                    "episodes_complete": None,
                                    "status": "red"  # Par défaut rouge si on ne peut pas vérifier
                                }
                                logger.warning(f"Impossible de vérifier les épisodes pour '{name}' (s{season}, {langage}) - retour None")
                            elif episodes_complete:
                                # Tous les épisodes sont téléchargés
                                anime_entry = {
                                    "name": name,
                                    "season": season,
                                    "langage": langage,
                                    "found": True,
                                    "anime_day": day_id,
                                    "day_id": None,
                                    "episodes_complete": True,
                                    "status": "green"  # Tout téléchargé
                                }
                                logger.info(f"Anime '{name}' (single_download): tous les épisodes sont téléchargés")
                            else:
                                # Pas tous les épisodes téléchargés
                                anime_entry = {
                                    "name": name,
                                    "season": season,
                                    "langage": langage,
                                    "found": True,
                                    "anime_day": day_id,
                                    "day_id": None,
                                    "episodes_complete": False,
                                    "status": "yellow"  # Pas fini de télécharger
                                }
                                logger.info(f"Anime '{name}' (single_download): pas tous les épisodes téléchargés")
                        
                        self.anime_list.append(anime_entry)
            
            # Traiter auto_download (animes par jour)
            if "auto_download" in entry:
                auto_download = entry["auto_download"]
                logger.debug(f"  auto_download trouvé avec {len(auto_download)} jours")
                
                if not isinstance(auto_download, dict):
                    logger.warning(f"  auto_download n'est pas un dictionnaire dans l'entrée {entry_idx}")
                    continue
                
                for jour, anime_list in auto_download.items():
                    # Récupérer le day_id correspondant
                    day_id = jours_mapping.get(jour)
                    if day_id is None:
                        logger.warning(f"Jour '{jour}' non reconnu, ignoré")
                        continue
                    
                    # Traiter single_download différemment (ne pas chercher dans le planning)
                    is_single_download = (jour == "single_download")
                    
                    if not isinstance(anime_list, list):
                        logger.warning(f"  Liste d'animes pour '{jour}' n'est pas une liste, ignorée")
                        continue
                    
                    logger.debug(f"    Jour '{jour}' (id={day_id}): {len(anime_list)} animes")
                    
                    # Log spécial pour single_download
                    if jour == "single_download":
                        logger.info(f"Traitement de {len(anime_list)} animes single_download (jour 8)")
                    
                    # Parcourir tous les animes de ce jour
                    for anime in anime_list:
                        total_animes_checked += 1
                        
                        # Vérifier que c'est un anime anime-sama
                        streaming = anime.get("streaming")
                        if streaming != "anime-sama":
                            skipped_not_anime_sama += 1
                            logger.debug(f"Anime ignoré (streaming='{streaming}' au lieu de 'anime-sama'): {anime.get('name', 'N/A')}")
                            continue
                        
                        name = anime.get("name")
                        season = anime.get("season")
                        langage = anime.get("langage")
                        
                        if not name or not season or not langage:
                            skipped_incomplete += 1
                            logger.warning(f"Anime incomplet dans {jour}: {anime}")
                            continue
                        
                        # Traitement spécial pour single_download
                        if is_single_download:
                            # Pour single_download, on ne cherche pas dans le planning
                            # On vérifie juste si l'anime existe et si tous les épisodes sont téléchargés
                            
                            # Vérifier si l'anime existe sur anime-sama
                            anime_info = extract_anime_info(name)
                            
                            if anime_info is None:
                                # Anime non trouvé sur anime-sama
                                anime_entry = {
                                    "name": name,
                                    "season": season,
                                    "langage": langage,
                                    "found": False,
                                    "anime_day": day_id,
                                    "day_id": None,
                                    "episodes_complete": None,
                                    "status": "red"  # Pas trouvé
                                }
                                logger.debug(f"Anime '{name}' (single_download) - Non trouvé sur anime-sama")
                            else:
                                # Anime trouvé, vérifier les épisodes
                                episodes_complete = self.check_episodes_complete(name, season, langage)
                                
                                if episodes_complete is None:
                                    # Impossible de vérifier les épisodes
                                    anime_entry = {
                                        "name": name,
                                        "season": season,
                                        "langage": langage,
                                        "found": True,  # Trouvé sur anime-sama
                                        "anime_day": day_id,
                                        "day_id": None,
                                        "episodes_complete": None,
                                        "status": "red"  # Par défaut rouge si on ne peut pas vérifier
                                    }
                                    logger.warning(f"Impossible de vérifier les épisodes pour '{name}' (s{season}, {langage}) - retour None")
                                elif episodes_complete:
                                    # Tous les épisodes sont téléchargés
                                    anime_entry = {
                                        "name": name,
                                        "season": season,
                                        "langage": langage,
                                        "found": True,
                                        "anime_day": day_id,
                                        "day_id": None,
                                        "episodes_complete": True,
                                        "status": "green"  # Tout téléchargé
                                    }
                                    logger.info(f"Anime '{name}' (single_download): tous les épisodes sont téléchargés")
                                else:
                                    # Pas tous les épisodes téléchargés
                                    anime_entry = {
                                        "name": name,
                                        "season": season,
                                        "langage": langage,
                                        "found": True,
                                        "anime_day": day_id,
                                        "day_id": None,
                                        "episodes_complete": False,
                                        "status": "yellow"  # Pas fini de télécharger
                                    }
                                    logger.info(f"Anime '{name}' (single_download): pas tous les épisodes téléchargés")
                            
                            self.anime_list.append(anime_entry)
                        else:
                            # Traitement normal pour les autres jours (y compris no_day)
                            # Construire les variantes d'URL de l'anime (pour gérer les saisons "x-y")
                            anime_url_variants = self.build_anime_url_variants(name, season, langage)
                            
                            # Comparer avec le planning (vérifie toutes les variantes)
                            result = self.compare_planning(anime_url_variants, day_id)
                            
                            # Si pas trouvé dans le planning, vérifier les épisodes dans la database
                            episodes_complete = None
                            if not result["found"]:
                                logger.debug(f"Anime '{name}' non trouvé dans le planning, vérification des épisodes...")
                                episodes_complete = self.check_episodes_complete(name, season, langage)
                                if episodes_complete is None:
                                    logger.warning(f"Impossible de vérifier les épisodes pour '{name}' (s{season}, {langage}) - retour None")
                                else:
                                    logger.info(f"Vérification épisodes pour '{name}': {'complets' if episodes_complete else 'incomplets'}")
                            
                            # Sauvegarder dans anime_list
                            anime_entry = {
                                "name": name,
                                "season": season,
                                "langage": langage,
                                "found": result["found"],
                                "anime_day": result["anime_day"],  # Jour attendu
                                "day_id": result["day_id"],        # Jour où trouvé (ou None)
                            }
                            
                            # Ajouter episodes_complete seulement si l'anime n'est pas dans le planning
                            if episodes_complete is not None:
                                anime_entry["episodes_complete"] = episodes_complete
                            
                            self.anime_list.append(anime_entry)
                            
                            status_msg = 'Trouvé' if result['found'] else f'Non trouvé (épisodes: {"complets" if episodes_complete else "incomplets" if episodes_complete is False else "N/A"})'
                            logger.debug(f"Anime '{name}' (s{season}, {langage}) - Jour {jour} (id={day_id}): {status_msg}")
        
        # Log des statistiques de traitement
        logger.info(f"Animes vérifiés: {total_animes_checked}, ignorés (pas anime-sama): {skipped_not_anime_sama}, ignorés (incomplets): {skipped_incomplete}, traités: {len(self.anime_list)}")
        
        # Suppression automatique des animes selon les critères
        if self.auto_planning:
            deleted_count = self._auto_delete_animes()
            if deleted_count > 0:
                logger.info(f"Suppression automatique: {deleted_count} anime(s) supprimé(s) du fichier anime.json")
        else:
            logger.debug("auto_planning est désactivé, aucune suppression automatique")
                        
        logger.info(f"Comparaison terminée: {len(self.anime_list)} animes traités")
        return self.anime_list
    
    def _auto_delete_animes(self):
        """
        Supprime automatiquement les animes du fichier anime.json selon les critères :
        - Pour auto_download : si l'anime n'est plus dans le planning ET tous les épisodes sont installés
        - Pour single_download : si tous les épisodes sont installés
        
        Returns:
            int: Nombre d'animes supprimés
        """
        logger = universal_logger(name="Anime-sama - Planning Auto-Delete", log_file="anime-sama.log")
        
        if not self.anime_json_path or not self.anime_json_path.exists():
            logger.warning("Fichier anime.json non trouvé, impossible de supprimer des animes")
            return 0
        
        deleted_count = 0
        modified = False
        
        # Créer une copie profonde pour éviter de modifier pendant l'itération
        anime_json_copy = copy.deepcopy(self.anime_json)
        
        # Parcourir toutes les entrées
        for entry_idx, entry in enumerate(self.anime_json):
            if not isinstance(entry, dict):
                continue
            
            # Traiter single_download (supprimer si tous les épisodes sont installés)
            if "single_download" in entry:
                single_download_list = entry.get("single_download", [])
                if isinstance(single_download_list, list):
                    # Créer une nouvelle liste sans les animes à supprimer
                    new_single_download = []
                    for anime in single_download_list:
                        if not isinstance(anime, dict):
                            new_single_download.append(anime)
                            continue
                        
                        name = anime.get("name")
                        season = anime.get("season")
                        langage = anime.get("langage")
                        streaming = anime.get("streaming")
                        
                        # Vérifier si cet anime correspond à un résultat avec episodes_complete == True
                        should_delete = False
                        for result in self.anime_list:
                            if (result.get("name") == name and 
                                result.get("season") == season and 
                                result.get("langage") == langage and
                                result.get("anime_day") == "8"):  # single_download = jour 8
                                
                                if result.get("episodes_complete") is True:
                                    should_delete = True
                                    deleted_count += 1
                                    logger.info(f"Suppression automatique (single_download): {name} s{season} ({langage}) - tous les épisodes installés")
                                    break
                        
                        if not should_delete:
                            new_single_download.append(anime)
                    
                    # Mettre à jour la liste si des éléments ont été supprimés
                    if len(new_single_download) != len(single_download_list):
                        anime_json_copy[entry_idx]["single_download"] = new_single_download
                        modified = True
            
            # Traiter auto_download (supprimer si pas dans le planning ET tous les épisodes installés)
            if "auto_download" in entry:
                auto_download = entry.get("auto_download", {})
                if isinstance(auto_download, dict):
                    for jour, anime_list in auto_download.items():
                        if not isinstance(anime_list, list):
                            continue
                        
                        # Créer une nouvelle liste sans les animes à supprimer
                        new_anime_list = []
                        for anime in anime_list:
                            if not isinstance(anime, dict):
                                new_anime_list.append(anime)
                                continue
                            
                            name = anime.get("name")
                            season = anime.get("season")
                            langage = anime.get("langage")
                            streaming = anime.get("streaming")
                            
                            # Vérifier si cet anime correspond à un résultat avec found == False ET episodes_complete == True
                            should_delete = False
                            for result in self.anime_list:
                                if (result.get("name") == name and 
                                    result.get("season") == season and 
                                    result.get("langage") == langage):
                                    
                                    # Vérifier le jour correspondant
                                    jours_mapping = {
                                        "lundi": "0", "mardi": "1", "mercredi": "2", "jeudi": "3",
                                        "vendredi": "4", "samedi": "5", "dimanche": "6", "no_day": "7"
                                    }
                                    expected_day_id = jours_mapping.get(jour)
                                    
                                    if (result.get("anime_day") == expected_day_id and
                                        result.get("found") is False and
                                        result.get("episodes_complete") is True):
                                        should_delete = True
                                        deleted_count += 1
                                        logger.info(f"Suppression automatique (auto_download, {jour}): {name} s{season} ({langage}) - plus dans le planning et tous les épisodes installés")
                                        break
                            
                            if not should_delete:
                                new_anime_list.append(anime)
                        
                        # Mettre à jour la liste si des éléments ont été supprimés
                        if len(new_anime_list) != len(anime_list):
                            anime_json_copy[entry_idx]["auto_download"][jour] = new_anime_list
                            modified = True
        
        # Sauvegarder le fichier si des modifications ont été faites
        if modified:
            try:
                with open(self.anime_json_path, 'w', encoding='utf-8') as f:
                    json.dump(anime_json_copy, f, indent=4, ensure_ascii=False)
                
                # Mettre à jour self.anime_json pour refléter les changements
                self.anime_json = anime_json_copy
                
                logger.info(f"Fichier anime.json mis à jour avec succès ({deleted_count} anime(s) supprimé(s))")
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde de anime.json: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                deleted_count = 0  # Ne pas compter comme supprimé si la sauvegarde a échoué
        
        return deleted_count
