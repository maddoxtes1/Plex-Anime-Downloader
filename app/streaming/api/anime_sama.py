import os
from webbrowser import get
import requests
import re
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup
from configparser import ConfigParser

from ...sys import universal_logger, FolderConfig
from ...sys.database import anime_data_database, anime_details_database

def get_panning():
    """
    Récupère les URLs des animes depuis la page planning, organisées par jour (id 0-7).
    Ne récupère que les animes de type "Anime".
    - Jours 0-6 : jours de la semaine (lundi à dimanche)
    - Jour 7 : no_day (animes sans jour spécifique, dans le div scrollBarStyled)

    Returns:
        dict: Dictionnaire avec les clés "0" à "7" (jours de la semaine + no_day) et valeurs listes d'URLs
              Format: {"0": [url1, url2, ...], "1": [url3, ...], ..., "7": [url_no_day, ...]}
    """
    logger = universal_logger(name="Anime-sama - Planning", log_file="anime-sama.log")

    try:
        # Récupérer la configuration
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
        flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
        flaresolver_port = config.get("flaresolver", "port", fallback="8191")
        # Construire l'URL du planning
        planning_url = urljoin(as_baseurl.rstrip('/') + '/', 'planning/')
        logger.debug(f"Récupération du planning depuis: {planning_url}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": planning_url,
            "maxTimeout": 120000,
            "returnOnlyCookies": False
        }
        headers_flaresolver = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        raw_html_content = None

        # Tentative de requête directe
        try:
            response = requests.get(planning_url, timeout=30)
            if response.status_code == 403:
                logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
            else:
                response.raise_for_status() # Raises for other HTTP errors (e.g., 500)
                raw_html_content = response.content
                logger.debug("Requête directe réussie.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

        # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
        if raw_html_content is None and flaresolver_use == "true":
            logger.debug("Tentative de récupération via Flaresolver.")
            try:
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                flaresolver_json_response = response_flaresolver.json()
                if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                    raw_html_content = flaresolver_json_response['solution']['response']
                    logger.debug("Flaresolver a récupéré le contenu avec succès.")
                else:
                    logger.error("Réponse de Flaresolver ne contient pas le contenu HTML attendu.")
                    return {} # Retourne un dictionnaire vide si le contenu HTML n'est pas trouvé
            except Exception as e:
                logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                return {} # Retourne un dictionnaire vide en cas d'erreur Flaresolver
        elif raw_html_content is None and flaresolver_use != "true":
            logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de récupérer le planning.")
            return {}

        if raw_html_content is None:
            logger.error("Aucun contenu HTML n'a pu être récupéré après toutes les tentatives.")
            return {}

        soup = BeautifulSoup(raw_html_content, 'html.parser')

        # Dictionnaire pour stocker les URLs par jour (id 0-7, où 7 = no_day)
        planning_data = {}

        # Parcourir tous les divs avec id de 0 à 6 (jours de la semaine)
        for day_id in range(7):
            day_div = soup.find('div', {'id': str(day_id)})

            if not day_div:
                planning_data[str(day_id)] = []
                continue

            # Trouver tous les anime-card-premium avec la classe "Anime"
            # "Anime" est dans les classes CSS, pas dans data-card-type
            anime_cards = day_div.find_all('div', class_=lambda x: x and 'anime-card-premium' in x and 'Anime' in x if x else False)

            urls = []
            for card in anime_cards:
                # Trouver le lien <a> à l'intérieur
                link = card.find('a')
                if link:
                    href = link.get('href', '').strip()
                    if href:
                        # Convertir en URL absolue si nécessaire
                        if href.startswith('/'):
                            full_url = urljoin(as_baseurl, href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(as_baseurl + '/', href)
                        urls.append(full_url)

            planning_data[str(day_id)] = urls
            logger.debug(f"Jour {day_id}: {len(urls)} animes trouvés")

        # Traiter no_day (jour 7) - se trouve dans un div spécial avec scrollBarStyled
        no_day_div = soup.find('div', class_=lambda x: x and 'scrollBarStyled' in x and 'grabScroll' in x if x else False)

        if no_day_div:
            # Trouver tous les scan-card-premium avec la classe "Anime"
            # Les cartes no_day utilisent scan-card-premium au lieu de anime-card-premium
            anime_cards = no_day_div.find_all('div', class_=lambda x: x and 'scan-card-premium' in x and 'Anime' in x if x else False)

            urls = []
            for card in anime_cards:
                # Trouver le lien <a> à l'intérieur
                link = card.find('a')
                if link:
                    href = link.get('href', '').strip()
                    if href:
                        # Convertir en URL absolue si nécessaire
                        if href.startswith('/'):
                            full_url = urljoin(as_baseurl, href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(as_baseurl + '/', href)
                        urls.append(full_url)

            planning_data["7"] = urls  # Jour 7 = no_day
            logger.debug(f"Jour 7 (no_day): {len(urls)} animes trouvés")
        else:
            planning_data["7"] = []
            logger.debug("Jour 7 (no_day): div non trouvé")

        total_animes = sum(len(urls) for urls in planning_data.values())
        logger.debug(f"Total: {total_animes} animes récupérés depuis le planning")

        return planning_data

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion : {e}")
        return {}
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour le planning")
        return {}
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête : {e}")
        return {}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du planning : {e}")
        return {}

def get_anime_details(name):
    """
    Extrait les détails complets d'un anime depuis la page catalogue anime-sama.
    Inclut : titre, image, description, genres, liste des saisons disponibles.

    Utilise un système de cache pour éviter les requêtes HTTP répétées au site.
    Vérifie d'abord dans la base de données, et ne fait une requête HTTP que si nécessaire.

    Args:
        name: Nom de l'anime (ex: maou-no-musume-wa-yasashi-sugiru)

    Returns:
        dict: Dictionnaire avec 'title', 'image', 'description', 'genres', 'seasons' (liste), 'seasons_count', ou None en cas d'erreur
    """
    logger = universal_logger(name="Anime-sama - Extract Details", log_file="anime-sama.log")
    anime_name = name
    # Vérifier d'abord dans le cache
    try:
        # Récupérer le chemin de la base de données anime_details.json
        from ...sys import FolderConfig
        anime_details_path = FolderConfig.find_path(file_name="anime_details.json")
        if anime_details_path:
            details_db = anime_details_database(database_path=str(anime_details_path))
            cached_details = details_db.get_anime_details(anime_name)
            # Re-fetcher si cache incomplet (image / description / genres manquants)
            if cached_details is not None:
                has_image = bool(cached_details.get('image'))
                has_description = bool(cached_details.get('description')) and cached_details.get('description') != 'Description non disponible'
                has_genres = bool(cached_details.get('genres'))
                if has_image and has_description and has_genres:
                    logger.debug(f"Détails de '{anime_name}' récupérés depuis le cache (pas de requête HTTP)")
                    return cached_details
                logger.debug(
                    f"Cache incomplet pour '{anime_name}' "
                    f"(image={has_image}, description={has_description}, genres={has_genres}) — re-fetch"
                )
        else:
            logger.debug(f"Chemin anime_details.json non trouvé, pas de cache disponible")
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du cache pour '{anime_name}': {e}. Continuation avec requête HTTP.")

    # Si pas dans le cache, faire la requête HTTP
    try:
        # Récupérer la configuration pour obtenir as_baseurl
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
        flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
        flaresolver_port = config.get("flaresolver", "port", fallback="8191")

        # Construire l'URL à partir du name
        url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{anime_name}/')
        logger.debug(f"Extraction des détails depuis: {url}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 120000,
            "returnOnlyCookies": False
        }
        headers_flaresolver = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        raw_html_content = None

        # Tentative de requête directe
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 403:
                logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
            else:
                response.raise_for_status() # Raises for other HTTP errors (e.g., 500)
                raw_html_content = response.content
                logger.debug("Requête directe réussie.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

        # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
        if raw_html_content is None and flaresolver_use == "true":
            logger.debug("Tentative de récupération via Flaresolver.")
            try:
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                flaresolver_json_response = response_flaresolver.json()
                if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                    raw_html_content = flaresolver_json_response['solution']['response']
                    logger.debug("Flaresolver a récupéré le contenu avec succès.")
                else:
                    logger.error("Réponse de Flaresolver ne contient pas le contenu HTML attendu.")
                    return None # Retourne None si le contenu HTML n'est pas trouvé
            except Exception as e:
                logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                return None # Retourne None en cas d'erreur Flaresolver
        elif raw_html_content is None and flaresolver_use != "true":
            logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de récupérer les détails de l'anime.")
            return None

        if raw_html_content is None:
            logger.error("Aucun contenu HTML n'a pu être récupéré après toutes les tentatives.")
            return None

        soup = BeautifulSoup(raw_html_content, 'html.parser')

        # Extraire le titre : div.oeuvre-right > div.my-2 > h1
        titre_element = soup.select_one('div.oeuvre-right div.my-2 > h1')
        if not titre_element:
            titre_element = soup.find(
                'h1',
                class_=lambda c: c and 'text-4xl' in c and 'uppercase' in c and 'font-bold' in c
            )
        title = titre_element.get_text(strip=True) if titre_element else None

        # Extraire l'image : img#imgOeuvre (souvent injecté en JS) puis fallback og:image
        img_element = soup.find('img', {'id': 'imgOeuvre'})
        image = img_element.get('src', '').strip() if img_element else None
        if not image:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image = og_image['content'].strip()
                # Uniformiser vers le CDN jsDelivr utilisé ailleurs
                if 'raw.githubusercontent.com/Anime-Sama/IMG/img/' in image:
                    image = image.replace(
                        'https://raw.githubusercontent.com/Anime-Sama/IMG/img/',
                        'https://cdn.jsdelivr.net/gh/Anime-Sama/IMG@img/'
                    )

        # Extraire la description (p#synopsisText)
        desc_element = soup.find('p', {'id': 'synopsisText'})
        description = desc_element.get_text(strip=True) if desc_element else None

        # Extraire les genres (div.genres-wrap > span.genre-pill)
        genres = []
        genres_element = soup.find('div', class_='genres-wrap')
        if genres_element:
            genres = [
                g.get_text(strip=True)
                for g in genres_element.find_all('span', class_='genre-pill')
                if g.get_text(strip=True)
            ]

        # Extraire les saisons/versions depuis les scripts JavaScript (panneauAnime)
        # Les liens sont générés par JavaScript, donc on doit les extraire depuis les scripts
        seasons = []
        season_info = []  # Liste pour stocker les infos détaillées (nom, url)

        # Chercher tous les scripts dans la page
        scripts = soup.find_all('script')
        logger.debug(f"Scripts trouvés dans la page: {len(scripts)}")

        for script in scripts:
            script_content = script.string or ''
            if not script_content:
                continue

            # Chercher les appels panneauAnime("nom", "url")
            # Format: panneauAnime("Avec Fillers", "saison1/vostfr");
            # Pattern pour capturer uniquement les appels (pas la définition de fonction)
            # Exclure les lignes qui contiennent "function panneauAnime" pour éviter la définition
            # Remove JavaScript comments before parsing panneauAnime calls.
            # This prevents commented-out seasons from being detected.
            script_content = re.sub(
                r'/\*.*?\*/',
                '',
                script_content,
                flags=re.DOTALL
            )

            script_content = re.sub(
                r'//.*?$',
                '',
                script_content,
                flags=re.MULTILINE
            )

            # Find only active panneauAnime() calls.
            panneau_matches = re.findall(
                r'panneauAnime\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
                script_content,
                re.MULTILINE | re.DOTALL
            )
            if panneau_matches:
                logger.debug(f"Appels panneauAnime trouvés dans script: {len(panneau_matches)}")
            elif 'panneauAnime' in script_content:
                logger.debug(f"Script contient 'panneauAnime' mais pattern ne correspond pas. Extrait: {script_content[:200]}")

            for name, url in panneau_matches:
                # Filtrer : enlever les paramètres de fonction (nom, url) et ceux qui commencent par "scan/"
                # Vérifier si name ou url sont exactement "nom" ou "url" (paramètres de fonction)
                if name.strip().lower() == 'nom' or name.strip().lower() == 'url' or url.strip().lower() == 'nom' or url.strip().lower() == 'url':
                    logger.debug(f"Lien filtré (paramètre de fonction): name='{name}', url='{url}'")
                    continue

                if url.startswith('scan/'):
                    logger.debug(f"Lien filtré (scan/): {url}")
                    continue

                logger.debug(f"Lien trouvé depuis script - name: {name}, url: {url}")

                # Extraire le numéro de saison depuis l'URL pour la liste simple
                season_match = re.search(r'saison(\d+)', url, re.I)
                if season_match:
                    season_num = season_match.group(1)
                    if season_num not in seasons:
                        seasons.append(season_num)

                # Stocker les infos détaillées (nom, url)
                season_info.append({
                    'name': name,
                    'url': url
                })

        # Si pas trouvé dans les scripts, essayer de chercher dans les liens HTML (au cas où certains seraient déjà rendus)
        if not season_info:
            season_divs = soup.find_all('div', class_=lambda x: x and 'flex' in x and 'flex-wrap' in x and 'bg-slate-900' in x if x else False)
            logger.debug(f"Divs des saisons trouvés (fallback HTML): {len(season_divs)}")

            for season_div in season_divs:
                all_links = season_div.find_all('a', href=True)
                logger.debug(f"Liens trouvés dans un div (fallback): {len(all_links)}")

                for link in all_links:
                    href = link.get('href', '').strip()
                    if not href or href.startswith('scan/'):
                        continue

                    # Récupérer le nom depuis le div à l'intérieur
                    name_div = link.find('div', class_=lambda x: x and 'text-white' in x if x else False)
                    if not name_div:
                        name_div = link.find('div')

                    name = name_div.get_text(strip=True) if name_div else href

                    # Extraire le numéro de saison
                    season_match = re.search(r'saison(\d+)', href, re.I)
                    if season_match:
                        season_num = season_match.group(1)
                        if season_num not in seasons:
                            seasons.append(season_num)

                    season_info.append({
                        'name': name,
                        'url': href
                    })

        logger.debug(f"Résumé - Scripts analysés: {len(scripts)}, saisons extraites: {len(seasons)}, infos détaillées: {len(season_info)}")

        # Trier les saisons numériquement si possible
        def sort_season(s):
            # Essayer d'extraire un numéro
            num_match = re.search(r'(\d+)', str(s))
            if num_match:
                return int(num_match.group(1))
            return 999  # Mettre les saisons sans numéro à la fin

        seasons.sort(key=sort_season)

        result = {
            'title': title,
            'image': image,
            'description': description or 'Description non disponible',
            'genres': genres,
            'seasons': seasons,
            'seasons_count': len(seasons),
        }

        # Sauvegarder dans le cache pour les prochaines fois
        try:
            # Récupérer le chemin de la base de données anime_details.json
            anime_details_path = FolderConfig.find_path(file_name="anime_details.json")
            if anime_details_path:
                details_db = anime_details_database(database_path=str(anime_details_path))
                details_db.save_anime_details(anime_name, result)
                logger.debug(f"Détails de '{anime_name}' sauvegardés dans le cache")
            else:
                logger.debug(f"Chemin anime_details.json non trouvé, pas de sauvegarde en cache")
        except Exception as e:
            logger.warning(f"Erreur lors de la sauvegarde du cache pour '{anime_name}': {e}. Les détails sont quand même retournés.")

        logger.debug(f"Détails extraits avec succès pour '{anime_name}': {len(seasons)} saison(s) trouvée(s), {len(genres)} genre(s)")
        return result

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion pour '{anime_name}': {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour '{anime_name}'")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête pour '{anime_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails pour '{anime_name}': {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None

def get_episode_js(anime_name, anime_url, episode_js):
    """
    Télécharge un fichier JavaScript contenant les URLs des épisodes depuis une URL donnée.

    Cette fonction récupère le contenu d'un fichier JS depuis anime-sama et le sauvegarde
    localement pour traitement ultérieur. Le fichier contient généralement des variables
    JavaScript avec des tableaux d'URLs pour chaque épisode.

    Args:
        anime_name (str): Nom de l'anime (utilisé pour les logs)
        anime_url (str): URL complète du fichier JS à télécharger
        episode_js (str): Chemin local où sauvegarder le fichier JS téléchargé

    Returns:
        bool: True si le téléchargement et la sauvegarde ont réussi, False sinon

    Exemple:
        >>> get_episode_js(
        ...     anime_name="Naruto",
        ...     anime_url="https://anime-sama.tv/episodes/naruto.js",
        ...     episode_js="/path/to/naruto-episodes.js"
        ... )
        True
    """
    logger = universal_logger(name="Anime-sama - Download JS", log_file="anime-sama.log")

    try:
        # Récupérer la configuration de Flaresolver
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
        flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
        flaresolver_port = config.get("flaresolver", "port", fallback="8191")

        logger.debug(f"Téléchargement du fichier JS pour '{anime_name}' depuis: {anime_url}")
        logger.debug(f"Destination: {episode_js}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": anime_url,
            "maxTimeout": 120000,
            "returnOnlyCookies": False
        }
        headers_flaresolver = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        raw_content = None

        # Tentative de requête directe
        try:
            response = requests.get(anime_url, stream=True, timeout=30)
            if response.status_code == 403:
                logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
            else:
                response.raise_for_status()
                raw_content = response.iter_content(chunk_size=8192)
                logger.debug("Requête directe réussie.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

        # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
        if raw_content is None and flaresolver_use == "true":
            logger.debug("Tentative de récupération via Flaresolver.")
            try:
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                flaresolver_json_response = response_flaresolver.json()
                if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                    # Flaresolver retourne le contenu en texte, pas en stream
                    raw_content = [flaresolver_json_response['solution']['response'].encode('utf-8')] # Encoder pour l'écriture binaire
                    logger.debug("Flaresolver a récupéré le contenu avec succès.")
                else:
                    logger.error("Réponse de Flaresolver ne contient pas le contenu attendu.")
                    return False # Retourne False si le contenu n'est pas trouvé
            except Exception as e:
                logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                return False # Retourne False en cas d'erreur Flaresolver
        elif raw_content is None and flaresolver_use != "true":
            logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de télécharger le fichier JS.")
            return False

        if raw_content is None:
            logger.error("Aucun contenu n'a pu être récupéré après toutes les tentatives.")
            return False

        # Sauvegarder le contenu dans le fichier
        with open(episode_js, 'wb') as file:
            # Utiliser iter_content ou le contenu encodé de Flaresolver
            if isinstance(raw_content, list): # Si Flaresolver a retourné une liste (encodée)
                for chunk in raw_content:
                    file.write(chunk)
            else: # Si la requête directe a fonctionné (iter_content)
                for chunk in raw_content:
                    if chunk: # Filtrer les chunks vides
                        file.write(chunk)

        # Vérifier que le fichier a bien été créé et n'est pas vide
        if os.path.exists(episode_js) and os.path.getsize(episode_js) > 0:
            file_size = os.path.getsize(episode_js)
            logger.debug(f"Fichier JS téléchargé avec succès pour '{anime_name}' ({file_size} octets)")
            logger.debug(f"Fichier sauvegardé dans: {episode_js}")
            return True
        else:
            logger.warning(f"Le fichier JS pour '{anime_name}' a été créé mais est vide")
            return False

    except IOError as e:
        logger.error(f"Erreur d'écriture lors de la sauvegarde du fichier JS pour '{anime_name}': {e}")
        logger.debug(f"Chemin: {episode_js}")
        return False

    except Exception as e:
        logger.error(f"Erreur inattendue lors du téléchargement pour '{anime_name}': {e}")
        logger.debug(f"Type d'erreur: {type(e).__name__}")
        import traceback
        logger.debug(traceback.format_exc())
        return False

def get_anime_season(anime_name, anime_season_number):
    logger = universal_logger(name="Anime-sama - Search", log_file="anime-sama.log")
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding='utf-8')
    as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
    flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
    flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
    flaresolver_port = config.get("flaresolver", "port", fallback="8191")

    base_url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{anime_name}/')
    try:
        logger.debug(f"Extraction des détails depuis: {url}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 120000,
            "returnOnlyCookies": False
        }
        headers_flaresolver = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        raw_html_content = None

        # Tentative de requête directe
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 403:
                logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
            else:
                response.raise_for_status() # Raises for other HTTP errors (e.g., 500)
                raw_html_content = response.content
                logger.debug("Requête directe réussie.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

        # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
        if raw_html_content is None and flaresolver_use == "true":
            logger.debug("Tentative de récupération via Flaresolver.")
            try:
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                flaresolver_json_response = response_flaresolver.json()
                if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                    raw_html_content = flaresolver_json_response['solution']['response']
                    logger.debug("Flaresolver a récupéré le contenu avec succès.")
                else:
                    logger.error("Réponse de Flaresolver ne contient pas le contenu HTML attendu.")
                    return None # Retourne None si le contenu HTML n'est pas trouvé
            except Exception as e:
                logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                return None # Retourne None en cas d'erreur Flaresolver
        elif raw_html_content is None and flaresolver_use != "true":
            logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de récupérer les détails de l'anime.")
            return None

        if raw_html_content is None:
            logger.error("Aucun contenu HTML n'a pu être récupéré après toutes les tentatives.")
            return None

        soup = BeautifulSoup(raw_html_content, 'html.parser')




    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion pour '{anime_name}': {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour '{anime_name}'")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la reqûete pour '{anime_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails pour '{anime_name}': {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None












    results = []
    for season in anime_season_number:
        logger.info(f"{season}")
        url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{anime_name}/saison{season}/vostfr')
        logger.info(f"{url}")

        try:
            logger.debug(f"Extraction des détails depuis: {url}")

            # Définir les headers et data pour Flaresolver
            data_cloudflare = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 120000,
                "returnOnlyCookies": False
            }
            headers_flaresolver = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            raw_html_content = None

            # Tentative de requête directe
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 403:
                    logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
                else:
                    response.raise_for_status() # Raises for other HTTP errors (e.g., 500)
                    raw_html_content = response.content
                    logger.debug("Requête directe réussie.")
            except requests.exceptions.RequestException as e:
                logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

            # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
            if raw_html_content is None and flaresolver_use == "true":
                logger.debug("Tentative de récupération via Flaresolver.")
                try:
                    response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                    response_flaresolver.raise_for_status()
                    flaresolver_json_response = response_flaresolver.json()
                    if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                        raw_html_content = flaresolver_json_response['solution']['response']
                        logger.debug("Flaresolver a récupéré le contenu avec succès.")
                    else:
                        logger.error("Réponse de Flaresolver ne contient pas le contenu HTML attendu.")
                        return None # Retourne None si le contenu HTML n'est pas trouvé
                except Exception as e:
                    logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                    return None # Retourne None en cas d'erreur Flaresolver
            elif raw_html_content is None and flaresolver_use != "true":
                logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de récupérer les détails de l'anime.")
                return None

            if raw_html_content is None:
                logger.error("Aucun contenu HTML n'a pu être récupéré après toutes les tentatives.")
                return None

            soup = BeautifulSoup(raw_html_content, 'html.parser')

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erreur de connexion pour '{anime_name}': {e}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Délai d'attente dépassé pour '{anime_name}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la reqûete pour '{anime_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des détails pour '{anime_name}': {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

         # Recherche des conteneurs de langues
        language_container = soup.find('div', class_='flex flex-wrap justify-start mb-5')
        if not language_container:
            logger.error(f"Conteneur de langues non trouvé pour {anime_name} saison {season}")
            continue

        # Extraction des langues DISPONIBLES (ignore les éléments masqués)
        available_languages = []
        for lang_link in language_container.find_all('a', href=True):
            # 🔥 CORRECTION 2 : CHECK PYTHON VALIDE
            logger.info(f"LANGUE BRUTE -> href={lang_link.get('href')} " f"class={lang_link.get('class')} "f"style={lang_link.get('style')}")
            style = lang_link.get('style', '').lower()
            classes = lang_link.get('class', [])

            is_hidden = ('hidden' in classes or 'display: none' in style)

            if is_hidden:
                continue

            lang_code = lang_link['href'].rstrip('/').split('/')[-1]
            if lang_code and lang_code not in available_languages:
                available_languages.append(lang_code)
                logger.debug(f"Langue détectée : {lang_code}")

        # 🔥 CORRECTION 3 : AJOUTER RÉELLEMENT AU RESULTAT
        results.append({"season": season,"languages": available_languages})
        logger.info(f"Saison {season} : {len(available_languages)} langue(s) → {available_languages}")

    return results

def search_anime(value):
    logger = universal_logger(name="Anime-sama - Search",log_file="anime-sama.log")
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding='utf-8')
    as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
    flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true")
    flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
    flaresolver_port = config.get("flaresolver", "port", fallback="8191")

    url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/?type[]=Anime&annee_min=&annee_max=&episodes_min=&episodes_max=&chapitres_min=&chapitres_max=&search={value}&page=1')
    logger.debug(f"{url}")

    try:
        logger.debug(f"Extraction des détails depuis: {url}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 120000,
            "returnOnlyCookies": False
        }
        headers_flaresolver = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        raw_html_content = None

        # Tentative de requête directe
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 403:
                logger.warning("Requête directe bloquée par Cloudflare (403). Tentative avec Flaresolver si activé.")
            else:
                response.raise_for_status() # Raises for other HTTP errors (e.g., 500)
                raw_html_content = response.content
                logger.debug("Requête directe réussie.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"La requête directe a échoué ({e}). Tentative avec Flaresolver si activé.")

        # Si la requête directe a échoué ou a été bloquée par Cloudflare, essayer Flaresolver
        if raw_html_content is None and flaresolver_use == "true":
            logger.debug("Tentative de récupération via Flaresolver.")
            try:
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/", headers=headers_flaresolver, json=data_cloudflare)
                response_flaresolver.raise_for_status()
                flaresolver_json_response = response_flaresolver.json()
                if 'solution' in flaresolver_json_response and 'response' in flaresolver_json_response['solution']:
                    raw_html_content = flaresolver_json_response['solution']['response']
                    logger.debug("Flaresolver a récupéré le contenu avec succès.")
                else:
                    logger.error("Réponse de Flaresolver ne contient pas le contenu HTML attendu.")
                    return None # Retourne None si le contenu HTML n'est pas trouvé
            except Exception as e:
                logger.error(f"Erreur lors de la requête via Flaresolver : {e}")
                return None # Retourne None en cas d'erreur Flaresolver
        elif raw_html_content is None and flaresolver_use != "true":
            logger.error("La requête directe a échoué et Flaresolver est désactivé. Impossible de récupérer les détails de l'anime.")
            return None

        if raw_html_content is None:
            logger.error("Aucun contenu HTML n'a pu être récupéré après toutes les tentatives.")
            return None

        soup = BeautifulSoup(raw_html_content, 'html.parser')

        # Extraction de tous les href des catalog cards

        catalog_hrefs = []
        for card in soup.find_all('a', href=True):
            href = card.get('href', '')

            if '/catalogue/' in href:
                catalog_hrefs.append(href)

        logger.debug(f"Nombre de catalog cards trouvées : {len(catalog_hrefs)}")
        logger.debug(f"Catalog cards: {catalog_hrefs}")

        anime_detail = []
        for url in catalog_hrefs:
            name = url.split('/catalogue/')[-1].strip('/')

            anime = get_anime_details(name)

            if anime:
                anime["url"] = url

            anime_detail.append(anime)

        logger.debug(f"Catalog cards: {anime_detail}")
        return anime_detail

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion pour '{anime_name}': {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour '{anime_name}'")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête pour '{anime_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails pour '{anime_name}': {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None

class get_anime_episodes_url:
    """
    Classe unifiée pour extraire et sauvegarder les épisodes d'anime depuis des fichiers JavaScript.

    Cette classe combine les fonctionnalités de traitement d'un seul fichier JS ou de plusieurs fichiers JS
    en une seule interface. Elle détecte automatiquement le type d'entrée et applique la logique appropriée.

    Fonctionnalités principales :
    - Extraction des URLs d'épisodes depuis des fichiers JavaScript contenant des variables avec des tableaux d'URLs
    - Filtrage par domaine selon une whitelist (video.sibnet.ru, oneupload.to, vidmoly.to, sendvid.com)
    - Combinaison automatique de plusieurs fichiers JS avec numérotation continue des épisodes
    - Sauvegarde dans la base de données avec gestion du statut des épisodes existants

    Args:
        path_list (tuple): Tuple contenant (path_name, serie_name, season_name)
            - path_name: Chemin de base pour la série
            - serie_name: Nom de la série
            - season_name: Nom de la saison (ex: "season1")

        episode_js_or_list (str | list): Soit un chemin vers un fichier JS (str), soit une liste de chemins (list)
            - Si str: Traite un seul fichier JS contenant les URLs des épisodes
            - Si list: Combine tous les fichiers JS de la liste avec une numérotation continue des épisodes

    Processus de traitement :
        1. Initialise la série et la saison dans la base de données
        2. Détecte automatiquement si episode_js_or_list est une liste ou un seul fichier
        3. Pour chaque fichier JS :
           - Lit le contenu et extrait les variables JavaScript avec pattern: var nom = [url1, url2, ...];
           - Identifie le domaine le plus fréquent pour chaque variable
           - Filtre les URLs selon la whitelist de domaines autorisés
           - Remplace les URLs de domaines non autorisés par "none"
        4. Combine les épisodes de tous les fichiers (si liste) avec numérotation continue (01, 02, 03, ...)
        5. Sauvegarde chaque épisode dans la base de données :
           - Format du nom: "{serie_name} s{season_number} {episode_num}.mp4"
           - Préserve le statut existant si l'épisode existe déjà
           - Crée un nouvel épisode avec statut "not_downloaded" si inexistant

    Exemple d'utilisation :
        # Traiter un seul fichier
        get_anime_episodes(
            path_list=("path/to/serie", "Naruto", "season1"),
            episode_js_or_list="/path/to/episodes.js"
        )

        # Traiter plusieurs fichiers (parties)
        get_anime_episodes(
            path_list=("path/to/serie", "Naruto", "season1"),
            episode_js_or_list=["/path/to/part1.js", "/path/to/part2.js", "/path/to/part3.js"]
        )

    Note:
        Les fichiers JS vides ou contenant uniquement des commentaires multi-lignes sont ignorés.
        Les domaines non présents dans la whitelist sont remplacés par "none".
    """
    def __init__(self, path_list, episode_js_or_list):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        self.whitelist = ['video.sibnet.ru', 'vidmoly.to','vidmoly.biz','vidmoly.org','vidmoly.me','ansembed.net','oneupload.to','sendvid.com','uqload.vc','uqload.is','callistanise.com','minochinos.com']

        path_name, serie_name, season_name = path_list
        self.path_name = path_name
        self.serie_name = serie_name
        self.season_name = season_name

        db = anime_data_database()
        db.add_series(path_name, serie_name)
        db.add_season(path_name, serie_name, season_name)

        # Détecter si c'est une liste ou un seul fichier
        if isinstance(episode_js_or_list, list):
            # Traiter plusieurs fichiers (ancien extract_all_part_episode)
            self.combine_all_episodes(episode_js_or_list)
        else:
            # Traiter un seul fichier (ancien extract_link)
            self.process_single_file(episode_js_or_list)

    def convert_js_to_urls(self, episode_js):
        """Extrait les URLs d'un fichier episode_js"""
        try:
            with open(episode_js, "r", encoding="utf-8") as js_file:
                js_content = js_file.read()
        except FileNotFoundError:
            self.logger.warning(f"Fichier {episode_js} non trouvé")
            return None

        if js_content.strip().startswith("/*") and js_content.strip().endswith("*/"):
            self.logger.debug(msg="Le fichier est un commentaire multi-ligne. Ignoré.")
            return None

        pattern = r"var\s+(\w+)\s*=\s*\[([^\]]+)\];"
        matches = re.findall(pattern, js_content)

        data = {}
        for variable_name, urls in matches:
            urls_list = [
                url.strip().strip("'").strip('"')
                for url in urls.split(",")
                if url.strip() and not url.startswith("'")
            ]

            if not urls_list:
                self.logger.debug(msg=f"La variable {variable_name} est vide.")
                continue

            numbered_urls = {str(i + 1): url for i, url in enumerate(urls_list)}
            data[variable_name] = numbered_urls

        if not data:
            self.logger.info(msg=f"le fichier.js est vide (surment a cause que l'anime est pas encore sortie)")
            return None

        # Mise à jour des domaines
        def extract_domain(url):
            domain = urlparse(url).netloc
            return domain

        updates = []
        for var_name, eps in data.items():
            domains = [extract_domain(url) for url in eps.values()]
            domain_counts = Counter(domains)
            most_common_domain, _ = domain_counts.most_common(1)[0]

            for key, url in eps.items():
                if extract_domain(url) != most_common_domain:
                    eps[key] = "none"

            updates.append((var_name, most_common_domain, eps))

        data_with_domains = {}
        for old_var_name, most_common_domain, eps in updates:
            data_with_domains[most_common_domain] = eps

        # Conversion finale des données
        domain_urls = {domain: [] for domain in self.whitelist}

        for domain in self.whitelist:
            if domain in data_with_domains:
                domain_urls[domain] = list(data_with_domains[domain].values())

        return domain_urls

    def combine_all_episodes(self, episode_js_list):
        """Combine tous les épisodes de tous les fichiers avec une numérotation continue"""
        all_combined_urls = {domain: [] for domain in self.whitelist}

        # Extraire et combiner les URLs de tous les fichiers
        for episode_js in episode_js_list:
            domain_urls = self.convert_js_to_urls(episode_js)
            if domain_urls is None:
                continue

            # Combiner les URLs de ce fichier avec celles déjà extraites
            for domain in self.whitelist:
                if domain_urls[domain]:
                    all_combined_urls[domain].extend(domain_urls[domain])

        # Trouver la longueur maximale (nombre total d'épisodes combinés)
        max_length = max(len(urls) for urls in all_combined_urls.values()) if any(all_combined_urls.values()) else 0

        if max_length == 0:
            self.logger.warning("Aucun épisode trouvé dans les fichiers")
            return

        # Ajouter tous les épisodes à la base de données avec numérotation continue
        self.save_episodes_to_db(all_combined_urls, max_length)

    def process_single_file(self, episode_js):
        """Traite un seul fichier JS"""
        domain_urls = self.convert_js_to_urls(episode_js)
        if domain_urls is None:
            return

        max_length = max(len(urls) for urls in domain_urls.values()) if any(domain_urls.values()) else 0
        if max_length == 0:
            self.logger.warning("Aucun épisode trouvé dans le fichier")
            return

        self.save_episodes_to_db(domain_urls, max_length)

    def save_episodes_to_db(self, domain_urls, max_length):
        """Sauvegarde les épisodes dans la base de données"""
        db = anime_data_database()
        for i in range(max_length):
            episode_num = str(i + 1).zfill(2)
            season_number = self.season_name.replace("season", "").strip()
            episode_name = f"{self.serie_name} s{season_number} {episode_num}.mp4"
            episode_urls = [
                urls[i] if i < len(urls) else "none"
                for domain, urls in domain_urls.items()
            ]

            current_status = "not_downloaded"
            db.add_episode(
                path_name=self.path_name,
                series_name=self.serie_name,
                season_name=self.season_name,
                episode_list=(episode_name, current_status, episode_urls)
            )
