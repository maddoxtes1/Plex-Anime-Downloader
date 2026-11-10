import requests
import json
import time
import re
import random
from configparser import ConfigParser
from bs4 import BeautifulSoup

from ...sys import universal_logger, FolderConfig
from ...sys.database import anime_details_database, anime_data_database
from ...sys.db_access import get_details_db


def get_panning():
    """
    Récupère le planning depuis l'API franime, organisé par jour (id 0-7).
    - Jours 0-6 : jours de la semaine (lundi à dimanche)
    - Jour 7 : animes sans jour spécifique (si le champ "jour" est absent ou invalide)

    Returns:
        dict: Dictionnaire avec les clés "0" à "7" (jours de la semaine + no_day) et valeurs listes d'animes
              Format: {"0": [{"id_anime": 42765, "saison": "3", "lang": "vf"}, ...], "1": [...], ..., "7": [...]}
    """
    logger = universal_logger(name="Franime - Planning", log_file="franime.log")
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding='utf-8')
    base_url = config.get("franime", "base_url", fallback="https://franime.fr")
    api_base_url = config.get("franime", "api_base_url", fallback="https://api.franime.fr")
    # Mapping des jours français vers les IDs (0-6 pour lundi-dimanche, 7 pour no_day)
    jour_mapping = {
        "lundi": "0",
        "mardi": "1",
        "mercredi": "2",
        "jeudi": "3",
        "vendredi": "4",
        "samedi": "5",
        "dimanche": "6"
    }

    try:
        api_url = f"{api_base_url}/api/calendrier_data"
        logger.debug(f"Récupération du planning depuis: {api_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{base_url}/',
            'Accept': 'application/json',
            'Origin': f'{base_url}',
        }
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error(f"Erreur 403 - Erreur lors de la récupération du planning. Vous êtes probablement bloqué géographiquement.")
                return {str(i): [] for i in range(8)}
            else:
                logger.error(f"Erreur HTTP {response.status_code} lors de la requête: {e}")
                return {str(i): [] for i in range(8)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête: {e}")
            return {str(i): [] for i in range(8)}

        data = response.json()

        # Dictionnaire pour stocker les animes par jour (id 0-7)
        planning_data = {str(i): [] for i in range(8)}  # Initialiser tous les jours (0-7)

        if "data" in data and isinstance(data["data"], list):
            for anime in data["data"]:
                jour = anime.get("jour", "").lower().strip()

                # Extraire les informations de l'anime
                anime_info = {
                    "id_anime": anime.get("id_anime"),
                    "saison": anime.get("saison"),
                    "lang": anime.get("lang")
                }

                # Trouver le jour correspondant
                if jour in jour_mapping:
                    day_id = jour_mapping[jour]
                    planning_data[day_id].append(anime_info)
                    logger.debug(f"Anime {anime_info['id_anime']} ajouté au jour {day_id} ({jour})")
                else:
                    # Jour non reconnu ou absent -> jour 7 (no_day)
                    planning_data["7"].append(anime_info)
                    logger.debug(f"Anime {anime_info['id_anime']} ajouté au jour 7 (no_day) - jour original: '{jour}'")

        # Log du nombre d'animes par jour
        for day_id in range(8):
            count = len(planning_data[str(day_id)])
            if count > 0:
                day_name = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche", "no_day"][day_id]
                logger.debug(f"Jour {day_id} ({day_name}): {count} animes trouvés")

        total_animes = sum(len(animes) for animes in planning_data.values())
        logger.debug(f"Total: {total_animes} animes récupérés depuis le planning franime")

        return planning_data

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion : {e}")
        return {str(i): [] for i in range(8)}
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour le planning")
        return {str(i): [] for i in range(8)}
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête : {e}")
        return {str(i): [] for i in range(8)}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du planning : {e}")
        return {str(i): [] for i in range(8)}

def get_anime_details(anime_id):
    """
    Extrait les détails complets d'un anime depuis l'API franime.
    Inclut : titre, image (affiche), description, genres (themes), liste des saisons disponibles.

    Utilise un système de cache pour éviter les requêtes HTTP répétées.
    Vérifie d'abord dans la base de données, et ne fait une requête HTTP que si nécessaire.

    Args:
        anime_id (int): ID de l'anime (ex: 42765)

    Returns:
        dict: Dictionnaire avec 'title', 'image', 'description', 'genres', 'seasons' (liste), 'seasons_count', ou None en cas d'erreur
    """
    logger = universal_logger(name="Franime - Extract Details", log_file="franime.log")
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding='utf-8')
    base_url = config.get("franime", "base_url", fallback="https://franime.fr")
    api_base_url = config.get("franime", "api_base_url", fallback="https://api.franime.fr")

    # Vérifier d'abord dans le cache
    try:
        details_db = get_details_db()
        # Utiliser anime_id comme clé (convertir en string pour la clé)
        cached_details = details_db.get_anime_details(str(anime_id))
        if cached_details is not None:
            logger.debug(f"Détails de l'anime ID '{anime_id}' récupérés depuis le cache (pas de requête HTTP)")
            return cached_details
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du cache pour l'anime ID '{anime_id}': {e}. Continuation avec requête HTTP.")

    # Si pas dans le cache, faire la requête HTTP
    try:
        api_url = f"{api_base_url}/api/animes"
        logger.debug(f"Extraction des détails depuis: {api_url} pour l'anime ID: {anime_id}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{base_url}/',
            'Accept': 'application/json',
            'Origin': f'{base_url}',
        }
        try:
            response = requests.get(api_url, headers=headers, timeout=60)  # Timeout plus long car le fichier est gros
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error(f"Erreur 403 - Erreur lors de la récupération des anime details. Vous êtes probablement bloqué géographiquement.")
                return None
            else:
                logger.error(f"Erreur HTTP {response.status_code} lors de la requête: {e}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête: {e}")
            return None

        # Parser le JSON (c'est un tableau d'objets)
        data = response.json()

        # Chercher l'anime par ID
        anime_data = None
        if isinstance(data, list):
            # Convertir anime_id en int pour la comparaison (comme dans get_anime_season_info)
            try:
                anime_id_int = int(anime_id)
            except (ValueError, TypeError):
                anime_id_int = anime_id

            for anime in data:
                if anime.get("id") == anime_id_int:
                    anime_data = anime
                    break

        if not anime_data:
            logger.warning(f"Anime avec ID {anime_id} non trouvé dans l'API")
            return None

        # Extraire les données nécessaires
        title = anime_data.get("title") or anime_data.get("titleO")  # Utiliser titleO si title est vide
        description = anime_data.get("description")
        themes = anime_data.get("themes", [])  # themes est déjà une liste
        affiche = anime_data.get("affiche")  # URL de l'affiche
        saisons_data = anime_data.get("saisons", [])

        # Extraire les numéros de saisons depuis les titres
        seasons = []
        for saison in saisons_data:
            title_saison = saison.get("title", "")
            # Extraire le numéro depuis "Saison 1", "Saison 2", etc.
            season_match = re.search(r'saison\s*(\d+)', title_saison, re.I)
            if season_match:
                season_num = season_match.group(1)
                if season_num not in seasons:
                    seasons.append(season_num)

        # Trier les saisons numériquement
        def sort_season(s):
            try:
                return int(s)
            except:
                return 999

        seasons.sort(key=sort_season)

        result = {
            'title': title,
            'image': affiche,  # Sauvegarder affiche comme image (cohérent avec anime-sama)
            'description': description or 'Description non disponible',
            'genres': themes,  # themes devient genres (cohérent avec anime-sama)
            'seasons': seasons,
            'seasons_count': len(seasons)
        }

        # Sauvegarder dans le cache
        try:
            details_db = get_details_db()
            # Utiliser anime_id (converti en string) comme clé
            details_db.save_anime_details(str(anime_id), result)
            logger.debug(f"Détails de l'anime ID '{anime_id}' sauvegardés dans le cache")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache pour l'anime ID '{anime_id}': {e}")

        return result

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion : {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour l'API franime")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête : {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON : {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails pour l'anime ID '{anime_id}': {e}")
        return None

class get_anime_episodes_url:
    def __init__(self, path_list, episode_js, name, season, langage, timer_on, timer_thread):
        self.logger = universal_logger(name="Franime - Get Episodes URL", log_file="franime.log")
        self.anime_id = name
        self.season_number = season
        self.language = langage
        self.path_list = path_list
        self.episode_js = episode_js
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        self.base_url = config.get("franime", "base_url", fallback="https://franime.fr")
        self.api_base_url = config.get("franime", "api_base_url", fallback="https://api.franime.fr")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.base_url}/',
            'Accept': 'application/json',
            'Origin': f'{self.base_url}',
        }
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
        flaresolver_port = config.get("flaresolver", "port", fallback=8191)

        self.flaresolver_url = f"http://{flaresolver_host}:{flaresolver_port}/v1"
        self.headers_flaresolver = {"Content-Type": "application/json"}

        self.path_name, self.serie_name, self.season_name = path_list
        self.db = anime_data_database()
        self.db.add_series(self.path_name, self.serie_name)
        self.db.add_season(self.path_name, self.serie_name, f"season {self.season_number}")

        self.ban = False


    def get_anime_season_info(self):
        """
        Récupère les informations des épisodes pour la saison spécifiée et génère toutes les URLs à traiter.
        Filtre automatiquement les épisodes déjà téléchargés.

        Pour chaque épisode:
        - Vérifie si le langage est disponible
        - Filtre les lecteurs selon une whitelist (sibnet, oneupload, vidmoly, sendvid)
        - Vérifie si l'épisode est déjà téléchargé (si oui, l'ignore)
        - Génère toutes les URLs (épisode + lecteur) pour les épisodes non téléchargés
        - Mélange aléatoirement toutes les URLs pour éviter les patterns prévisibles

        Returns:
            tuple: (urls_to_download, episodes_already_downloaded)
                - urls_to_download: Liste mélangée de tuples (episode_name, url) à traiter, ou None en cas d'erreur
                - episodes_already_downloaded: Dict {episode_name: (status, urls)} des épisodes déjà téléchargés
        """
        api_url = f"{self.api_base_url}/api/animes"
        self.logger.debug(f"Extraction des informations de saison depuis: {api_url} pour l'anime ID: {self.anime_id}")

        try:
            response = requests.get(api_url, headers=self.headers, timeout=60)  # Timeout plus long car le fichier est gros
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                self.logger.error(f"Erreur 403 - Erreur lors de la récupération des anime details, Vous êtes probablement bloqué géographiquement.")
                return None, {}
            else:
                self.logger.error(f"Erreur HTTP {response.status_code} lors de la requête: {e}")
                return None, {}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de la requête: {e}")
            return None, {}

        # Parser le JSON (c'est un tableau d'objets)
        data = response.json()

        # Chercher l'anime par ID (comme dans get_anime_details)
        anime_data = None
        if isinstance(data, list):
            # Convertir self.anime_id en int pour la comparaison (comme dans get_anime_details)
            try:
                anime_id_int = int(self.anime_id)
            except (ValueError, TypeError):
                anime_id_int = self.anime_id

            for anime in data:
                if anime.get("id") == anime_id_int:
                    anime_data = anime
                    break

        if not anime_data:
            self.logger.error(f"Anime avec ID {self.anime_id} non trouvé dans l'API")
            return None, {}

        # Vérifier les saisons
        if not anime_data.get('saisons'):
            self.logger.error(f"Aucune saison trouvée dans les données pour {self.serie_name}")
            return None, {}

        if int(self.season_number) > len(anime_data['saisons']):
            self.logger.error(f"La saison {self.season_number} n'existe pas pour {self.serie_name}")
            return None, {}

        season_index = int(self.season_number) - 1

        if not anime_data['saisons'][season_index].get('episodes'):
            self.logger.error(f"Aucun épisode trouvé pour la saison {self.season_number}")
            return None, {}

        # Récupérer les épisodes déjà téléchargés pour les exclure
        existing_episodes = self.db.get_episode(self.path_name, self.serie_name, self.season_name)
        existing_episodes_dict = {ep[0]: (ep[1], ep[2]) for ep in existing_episodes}  # {episode_name: (status, url)}

        # Liste pour stocker toutes les URLs à traiter (épisode + lecteur)
        all_urls_to_process = []
        episodes_already_downloaded = {}  # {episode_name: (status, urls)}
        whitelist = ['sibnet', 'oneupload', 'vidmoly', 'sendvid', "minochinos", "uqload", "ansembed", "callistanise"]

        for ep_idx, episode in enumerate(anime_data['saisons'][season_index]['episodes']):
            if self.language not in episode.get('lang', {}):
                self.logger.debug(f"Le langage {self.language} n'est pas disponible pour l'épisode {ep_idx+1}")
                continue

            if not episode['lang'][self.language].get('lecteurs'):
                self.logger.debug(f"Aucun lecteur disponible en {self.language} pour l'épisode {ep_idx+1}")
                continue

            lecteurs = episode['lang'][self.language]['lecteurs']
            episode_name = f"{self.serie_name} s{self.season_number} {str(ep_idx + 1).zfill(2)}"

            # Vérifier si l'épisode est déjà téléchargé
            if episode_name in existing_episodes_dict:
                episode_status, existing_urls = existing_episodes_dict[episode_name]
                if episode_status != "not_downloaded":
                    # Épisode déjà téléchargé, l'ajouter à la liste des épisodes déjà téléchargés
                    episodes_already_downloaded[episode_name] = (episode_status, existing_urls)
                    self.logger.debug(f"Épisode {episode_name} déjà téléchargé, ignoré")
                    continue

            # Pour chaque lecteur, créer l'URL si le lecteur est valide (dans la whitelist)
            for lecteur_idx, lecteur in enumerate(lecteurs):
                # Vérifier si le lecteur est dans la whitelist
                if any(w in lecteur.lower() for w in whitelist):
                    # Créer l'URL pour cet épisode + ce lecteur
                    url = f"{self.api_base_url}/api/anime/{int(self.anime_id)}/{season_index}/{ep_idx}/{self.language}/{lecteur_idx}"
                    all_urls_to_process.append((episode_name, url))

        if not all_urls_to_process and not episodes_already_downloaded:
            self.logger.error("Aucun épisode trouvé avec les critères spécifiés")
            return None, {}

        # Mélanger aléatoirement toutes les URLs pour éviter les patterns prévisibles
        random.shuffle(all_urls_to_process)
        self.logger.debug(
            f"Total de {len(all_urls_to_process)} URLs générées et mélangées aléatoirement. "
            f"{len(episodes_already_downloaded)} épisodes déjà téléchargés ignorés."
        )

        return all_urls_to_process, episodes_already_downloaded

    def get_episodes_url(self, urls_to_process, episodes_already_downloaded):
        """
        Fait uniquement les requêtes HTTP pour récupérer les URLs des épisodes.
        Regroupe les résultats par épisode et intègre les épisodes déjà téléchargés.

        Args:
            urls_to_process: Liste de tuples (episode_name, url) à traiter
            episodes_already_downloaded: Dict {episode_name: (status, urls)} des épisodes déjà téléchargés

        Returns:
            list: Liste de tuples (episode_name, current_status, episode_urls) formatée pour add_episode
        """
        # Dictionnaire pour regrouper les URLs par épisode
        episode_urls_dict = {}  # {episode_name: [list of iframe URLs]}

        # Ajouter les épisodes déjà téléchargés
        for episode_name, (status, urls) in episodes_already_downloaded.items():
            episode_urls_dict[episode_name] = urls

        # Faire les requêtes pour les nouveaux épisodes
        results = []  # Liste de (episode_name, iframe_url)

        for episode_name, url in urls_to_process:
            if self.ban:
                break

            # Attendre AVANT la requête à l'API franime (comme dans testfranimeban.py)
            # Ajouter une variation aléatoire pour éviter les patterns prévisibles
            wait_time = 10 + random.uniform(0, 5)  # Entre 10 et 15 secondes
            time.sleep(wait_time)

            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    self.logger.error(f"Erreur 403 - Erreur lors de la récupération des urls. Vous êtes probablement bloqué géographiquement.")
                    continue
                else:
                    self.logger.error(f"Erreur HTTP {response.status_code} lors de la requête: {e}")
                    continue
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Erreur lors de la requête: {e}")
                continue

            video_url = response.text.strip()

            if not video_url.startswith(f"{self.base_url}/watch2"):
                if video_url.startswith("https://sibnet.ru/shell.php?videoid=") or video_url.startswith("https://video.sibnet.ru/shell.php?videoid="):
                    self.logger.error(f"tu vien de etre ban de franime je ne sais pas quand tu sera unban vien me montrer tes logs sur discord (https://discord.gg/DjfmPT8E4p)")
                    self.ban = True
                    break
                else:
                    self.logger.error(f"Erreur lors de la requête à franime: {video_url}")
                    continue

            data_cloudflare = {
                "cmd": "request.get",
                "url": video_url,
                "maxTimeout": 120000,
                "returnOnlyCookies": False
            }
            try:
                response_flaresolver = requests.post(self.flaresolver_url, headers=self.headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                result = response_flaresolver.json()
            except Exception as e:
                self.logger.error(f"Erreur lors de la requête à Flaresolver: il est peut etre pas disponible sur votre resaux essayer de changer le host")
                continue

            if result.get("status") == "ok":
                solution = result.get("solution", {})
                response_text = solution.get("response", "")

                soup = BeautifulSoup(response_text, 'html.parser')
                iframe = soup.find('iframe', src=True)
                if iframe:
                    iframe_src = iframe.get('src')
                    if iframe_src and iframe_src.strip():
                        results.append((episode_name, iframe_src.strip()))
                else:
                    self.logger.warning(f"Aucun iframe trouvé dans la réponse pour l'URL: {video_url}")
            else:
                self.logger.error(f"Erreur lors de la requête à Flaresolver: {result.get('message', 'Unknown error')}")

            # Petit délai après Flaresolver
            time.sleep(2)

        # Ajouter les nouveaux résultats au dictionnaire
        for episode_name, iframe_url in results:
            if episode_name not in episode_urls_dict:
                episode_urls_dict[episode_name] = []
            episode_urls_dict[episode_name].append(iframe_url)

        # Construire la liste finale formatée
        episode_lists = []
        for episode_name, episode_urls in episode_urls_dict.items():
            current_status = "not_downloaded"
            if episode_urls:
                episode_lists.append((episode_name, current_status, episode_urls))
            else:
                self.logger.warning(f"Aucune URL récupérée pour l'épisode {episode_name}")

        # Trier les épisodes du premier au dernier (extraire le numéro d'épisode depuis le nom)
        def extract_episode_number(episode_tuple):
            episode_name = episode_tuple[0]
            # Format: "Serie Name s1 01" -> extraire "01"
            match = re.search(r's\d+\s+(\d+)', episode_name)
            if match:
                return int(match.group(1))
            return 999  # Si on ne trouve pas le numéro, mettre à la fin

        episode_lists.sort(key=extract_episode_number)

        return episode_lists

    def add_episode(self, episode_lists):
        for episode_name, current_status, episode_urls in episode_lists:
            self.db.add_episode(
                path_name=self.path_name,
                series_name=self.serie_name,
                season_name=self.season_name,
                episode_list=(episode_name, current_status, episode_urls)
            )

    def run(self):
        # Récupérer les URLs à traiter et les épisodes déjà téléchargés (tout est géré dans get_anime_season_info)
        urls_to_download, episodes_already_downloaded = self.get_anime_season_info()

        if urls_to_download is None:
            self.logger.error("Aucun épisode trouvé")
            return None

        self.logger.debug(f"URLs to download: {urls_to_download}")
        self.logger.debug(f"Episodes already downloaded: {episodes_already_downloaded}")

        # Faire les requêtes et regrouper les résultats (tout est géré dans get_episodes_url)
        episode_lists = self.get_episodes_url(urls_to_download, episodes_already_downloaded)

        # Sauvegarder dans la base de données
        if episode_lists:
            self.add_episode(episode_lists)

        return self.ban
