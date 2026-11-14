import os
from webbrowser import get
import requests
import re
import json
import time
import random
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup
from configparser import ConfigParser

from ...sys import universal_logger, FolderConfig
from ...sys.database import anime_data_database, anime_details_database
from ...sys.db_access import get_details_db

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
        flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true").strip().lower()
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
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/v1", headers=headers_flaresolver, json=data_cloudflare, timeout=130)
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
        details_db = get_details_db()
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
    except Exception as e:
        logger.warning(f"Erreur lors de la lecture du cache pour '{anime_name}': {e}. Continuation avec requête HTTP.")

    # Si pas dans le cache, faire la requête HTTP
    try:
        # Récupérer la configuration pour obtenir as_baseurl
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true").strip().lower()
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
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/v1", headers=headers_flaresolver, json=data_cloudflare, timeout=130)
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
            details_db = get_details_db()
            details_db.save_anime_details(anime_name, result)
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

BDD_SCRIPT_PATTERN = re.compile(
    r'<script[^>]*data-source=["\']bdd["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


# ----------------------------------------------------------------------------
# Helpers HTTP (partagés par les deux)
# ----------------------------------------------------------------------------
def load_flaresolver_config():
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding="utf-8")
    return {
        "use": config.get("flaresolver", "use_flaresolver", fallback="true").strip().lower() == "true",
        "host": config.get("flaresolver", "host", fallback="flaresolver"),
        "port": config.get("flaresolver", "port", fallback="8191"),
    }


def _strip_flaresolver_wrapper(body):
    """Flaresolver enveloppe parfois du texte/JSON brut dans <html><body><pre>...</pre>."""
    match = re.search(r"<pre[^>]*>(.*?)</pre>", body, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else body


def http_get_text(url, referer, logger, fs_conf, is_html=True, force_flaresolver=False):
    """
    GET direct, puis Flaresolver en secours (403 / erreur / Cloudflare).
    Avec force_flaresolver=True, saute la requête directe.
    Retourne le texte de la réponse ou None.
    """
    headers = {"User-Agent": BROWSER_UA, "Referer": referer, "Accept": "*/*"}

    # 1) Requête directe
    if not force_flaresolver:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 403:
                logger.warning(f"Requête directe bloquée (403) : {url}")
            else:
                response.raise_for_status()
                return response.text
        except requests.exceptions.RequestException as e:
            logger.warning(f"Requête directe échouée ({e}) : {url}")

    # 2) Flaresolver
    if not fs_conf["use"]:
        logger.error("Requête directe échouée et Flaresolver désactivé.")
        return None

    try:
        r = requests.post(
            f"http://{fs_conf['host']}:{fs_conf['port']}/v1",
            headers={"Content-Type": "application/json"},
            json={"cmd": "request.get", "url": url, "maxTimeout": 120000, "returnOnlyCookies": False},
            timeout=130,
        )
        r.raise_for_status()
        solution = r.json().get("solution", {})
        body = solution.get("response")
        if body is None:
            logger.error("Réponse Flaresolver sans contenu.")
            return None
        return body if is_html else _strip_flaresolver_wrapper(body)
    except Exception as e:
        logger.error(f"Erreur Flaresolver : {e}")
        return None


# ----------------------------------------------------------------------------
# 1) Téléchargement de la page + extraction du <script data-source="bdd">
# ----------------------------------------------------------------------------
def get_episode_js(anime_name, anime_url, episode_js):
    """
    Récupère la page d'une saison anime-sama et sauvegarde le contenu du
    <script data-source="bdd"> (variables epsX, epsMeta, epsJeton) dans `episode_js`.

    Args:
        anime_name (str): Nom de l'anime (logs)
        anime_url (str): URL de la page, ex:
            https://anime-sama.to/catalogue/firefly-wedding/saison1/vostfr/
        episode_js (str): Chemin local où sauvegarder le contenu du script

    Returns:
        bool: True si le script a été trouvé et sauvegardé, False sinon
    """
    logger = universal_logger(name="Anime-sama - Download JS", log_file="anime-sama.log")

    try:
        fs_conf = load_flaresolver_config()
        logger.debug(f"Téléchargement de la page pour '{anime_name}' : {anime_url}")

        html = http_get_text(anime_url, referer=anime_url, logger=logger, fs_conf=fs_conf)
        if not html:
            logger.error(f"Impossible de récupérer la page pour '{anime_name}'.")
            return False

        match = BDD_SCRIPT_PATTERN.search(html)
        if not match:
            logger.error(f"Balise <script data-source=\"bdd\"> introuvable pour '{anime_name}'.")
            return False

        script_content = match.group(1).strip()
        if "epsJeton" not in script_content:
            logger.error(f"Le script trouvé ne contient pas epsJeton pour '{anime_name}'.")
            return False

        with open(episode_js, "w", encoding="utf-8") as f:
            f.write(script_content)

        if os.path.getsize(episode_js) > 0:
            logger.debug(f"Script sauvegardé pour '{anime_name}' ({os.path.getsize(episode_js)} octets)")
            return True

        logger.warning(f"Le fichier pour '{anime_name}' est vide")
        return False

    except IOError as e:
        logger.error(f"Erreur d'écriture pour '{anime_name}' : {e}")
        return False
    except Exception as e:
        import traceback
        logger.error(f"Erreur inattendue pour '{anime_name}' : {e}")
        logger.debug(traceback.format_exc())
        return False

def get_anime_season(anime_name, anime_season_number):
    logger = universal_logger(name="Anime-sama - Search", log_file="anime-sama.log")
    config_path = FolderConfig.find_path(file_name="config.conf")
    config = ConfigParser(allow_no_value=True)
    config.read(config_path, encoding='utf-8')
    as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
    flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true").strip().lower()
    flaresolver_host = config.get("flaresolver", "host", fallback="flaresolver")
    flaresolver_port = config.get("flaresolver", "port", fallback="8191")

    base_url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{anime_name}/')
    try:
        logger.debug(f"Extraction des détails depuis: {base_url}")

        # Définir les headers et data pour Flaresolver
        data_cloudflare = {
            "cmd": "request.get",
            "url": base_url,
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
            response = requests.get(base_url, timeout=30)
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
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/v1", headers=headers_flaresolver, json=data_cloudflare, timeout=130)
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

        # Recherche de l'élément correspondant à la saison demandée
        season_key = f"saison{anime_season_number}"

        # Chercher les éléments avec des attributs href contenant la saison
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if season_key in href:
                # Extraire le language après le slash
                parts = href.split('/')
                if len(parts) > 1:
                    lang = parts[-1]  # Le dernier élément est le language
                    logger.debug(f"Trouvé le language pour la saison {anime_season_number}: {lang}")
                    return lang

        # Si on n'a pas trouvé avec la saison, chercher tous les liens vostfr
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if 'vostfr' in href:
                parts = href.split('/')
                if len(parts) > 1:
                    lang = parts[-1]
                    logger.debug(f"Trouvé le language par défaut vostfr: {lang}")
                    return lang

        logger.warning(f"Aucun language trouvé pour la saison {anime_season_number} ou vostfr par défaut")
        return None

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
                    response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/v1", headers=headers_flaresolver, json=data_cloudflare, timeout=130)
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
    flaresolver_use = config.get("flaresolver", "use_flaresolver", fallback="true").strip().lower()
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
                response_flaresolver = requests.post(f"http://{flaresolver_host}:{flaresolver_port}/v1", headers=headers_flaresolver, json=data_cloudflare, timeout=130)
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
    Extrait les épisodes d'un (ou plusieurs) script(s) anime-sama et les sauvegarde en DB.

    Fonctionnement :
        - epsN = un lecteur (source), l'index dans le tableau = le numéro d'épisode
          (index 0 -> épisode 1, etc.). Chaque entrée est "lien:ID" (ou "" si absent).
        - epsMeta associe chaque ID à son domaine : {"78928": ["ansembed.net"], ...}
        - Si le domaine n'est pas dans la whitelist -> ignoré (donne "none").
        - Pour chaque ID retenu : GET /api/lien.php?j={epsJeton}&l={ID} -> URL réelle.

    Args:
        path_list (tuple): (path_name, serie_name, season_name)
        episode_js_or_list (str | list): fichier du script, ou liste de fichiers
            (parties combinées avec numérotation continue des épisodes)
    """

    API_URL = "https://anime-sama.to/api/lien.php"

    # Pauses "réalistes" (en secondes, tirées au hasard dans l'intervalle)
    REQUEST_DELAY = (1.0, 2)  # entre chaque appel à lien.php (dans un même anime)
    ANIME_DELAY = (3.0, 5.0)    # entre chaque anime

    def __init__(self, path_list, episode_js_or_list):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        self.whitelist = [
            'video.sibnet.ru', 'vidmoly.to', 'vidmoly.biz', 'vidmoly.org', 'vidmoly.me',
            'ansembed.net', 'oneupload.to', 'sendvid.com', 'uqload.vc', 'uqload.is',
            'callistanise.com', 'minochinos.com',
        ]
        self.fs_conf = load_flaresolver_config()
        self._logged_api_sample = False

        path_name, serie_name, season_name = path_list
        self.path_name = path_name
        self.serie_name = serie_name
        self.season_name = season_name

        db = anime_data_database()
        db.add_series(path_name, serie_name)
        db.add_season(path_name, serie_name, season_name)

        files = episode_js_or_list if isinstance(episode_js_or_list, list) else [episode_js_or_list]
        self.process_files(files)

    # --- Parsing du script -------------------------------------------------
    def parse_script(self, episode_js):
        """
        Retourne (jeton, episodes) où episodes est une liste (1 élément par épisode)
        de dicts {domaine_whitelist: id_lien}. None si rien d'exploitable.
        """
        try:
            with open(episode_js, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            self.logger.warning(f"Fichier {episode_js} non trouvé")
            return None

        if not content.strip():
            self.logger.warning(f"Fichier {episode_js} vide")
            return None

        jeton_match = re.search(r'var\s+epsJeton\s*=\s*["\']([^"\']+)["\']', content)
        meta_match = re.search(r'var\s+epsMeta\s*=\s*(\{.*?\})\s*;', content, re.DOTALL)
        if not jeton_match or not meta_match:
            self.logger.warning("epsJeton ou epsMeta introuvable dans le fichier.")
            return None

        jeton = jeton_match.group(1)
        try:
            meta = json.loads(meta_match.group(1))
        except json.JSONDecodeError as e:
            self.logger.error(f"epsMeta illisible : {e}")
            return None

        # Tous les epsN (eps1, eps2, ...) dans l'ordre numérique
        eps_vars = []
        for m in re.finditer(r'var\s+eps(\d+)\s*=\s*(\[.*?\])\s*;', content, re.DOTALL):
            try:
                eps_vars.append((int(m.group(1)), json.loads(m.group(2))))
            except json.JSONDecodeError:
                self.logger.warning(f"eps{m.group(1)} illisible, ignoré.")
        eps_vars.sort(key=lambda x: x[0])

        if not eps_vars:
            self.logger.info("Aucune variable epsN (l'anime n'est probablement pas encore sorti).")
            return None

        nb_episodes = max(len(arr) for _, arr in eps_vars)
        episodes = [{} for _ in range(nb_episodes)]

        for _, arr in eps_vars:
            for idx, entry in enumerate(arr):
                if not entry:
                    continue
                link_id = entry.split(":", 1)[-1].strip()
                info = meta.get(link_id)
                if not info:
                    continue
                domain = info[0]
                if domain not in self.whitelist:
                    continue  # -> restera "none"
                # Un seul lien par domaine et par épisode (le premier rencontré)
                episodes[idx].setdefault(domain, link_id)

        return jeton, episodes

    # --- Résolution d'un ID en URL ----------------------------------------
    def _extract_url(self, body):
        """Gère une réponse JSON ou texte brut."""
        body = body.strip()
        try:
            data = json.loads(body)
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                # Format réel de l'API : {"u": "https://..."}
                for key in ("u", "url", "lien", "link", "src"):
                    if isinstance(data.get(key), str) and data[key].startswith("http"):
                        return data[key]
                # Fallback : première valeur qui ressemble à une URL
                for value in data.values():
                    if isinstance(value, str) and value.startswith("http"):
                        return value
            if isinstance(data, list) and data and isinstance(data[0], str):
                return data[0]
        except json.JSONDecodeError:
            pass
        body = body.strip('"\'')
        return body if body.startswith("http") else None

    def _api_error(self, body):
        """Retourne le message d'erreur si la réponse est {"erreur": "..."}, sinon None."""
        try:
            data = json.loads(body.strip())
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and "erreur" in data:
            return str(data["erreur"])
        return None

    def resolve_link(self, jeton, link_id, referer):
        url = f"{self.API_URL}?j={jeton}&l={link_id}"

        body = http_get_text(url, referer=referer, logger=self.logger, fs_conf=self.fs_conf, is_html=False)
        if not body:
            return "none"

        error = self._api_error(body)
        if error:
            # Une seule seconde chance : on réessaie via Flaresolver, puis on abandonne
            self.logger.warning(f"API a répondu '{error}' pour l'id {link_id}, tentative via Flaresolver.")
            if not self.fs_conf["use"]:
                return "none"
            body = http_get_text(
                url, referer=referer, logger=self.logger, fs_conf=self.fs_conf,
                is_html=False, force_flaresolver=True,
            )
            if not body or self._api_error(body):
                self.logger.error(f"Échec pour l'id {link_id}, on continue.")
                return "none"

        if not self._logged_api_sample:  # utile pour ajuster le parsing si besoin
            self.logger.debug(f"Exemple de réponse API : {body[:200]}")
            self._logged_api_sample = True

        resolved = self._extract_url(body)
        if not resolved:
            self.logger.warning(f"Réponse API inattendue pour l'id {link_id} : {body[:100]}")
            return "none"
        return resolved

    # --- Traitement --------------------------------------------------------
    def process_files(self, episode_js_list):
        all_episodes = []  # liste de {domaine: url}, numérotation continue entre fichiers
        made_requests = False

        for episode_js in episode_js_list:
            parsed = self.parse_script(episode_js)
            if parsed is None:
                continue
            jeton, episodes = parsed

            referer = "https://anime-sama.to/"
            total_links = sum(len(ep) for ep in episodes)
            self.logger.info(
                f"Récupération de {total_links} liens pour {self.serie_name} - {self.season_name} "
                f"({len(episodes)} épisodes)"
            )
            for ep in episodes:
                resolved = {}
                for domain, link_id in ep.items():
                    resolved[domain] = self.resolve_link(jeton, link_id, referer)
                    made_requests = True
                    delay = random.uniform(*self.REQUEST_DELAY)
                    self.logger.debug(f"Pause de {delay:.1f}s avant le prochain lien")
                    time.sleep(delay)  # pause entre chaque lien
                all_episodes.append(resolved)

        if all_episodes:
            self.save_episodes_to_db(all_episodes)
        else:
            self.logger.warning("Aucun épisode trouvé dans les fichiers")

        # Pause entre chaque anime (seulement si on a vraiment tapé sur l'API)
        if made_requests:
            delay = random.uniform(*self.ANIME_DELAY)
            self.logger.info(f"Pause de {delay:.1f}s avant le prochain anime")
            time.sleep(delay)

    def save_episodes_to_db(self, episodes):
        db = anime_data_database()
        season_number = self.season_name.replace("season", "").strip()

        for i, ep_urls in enumerate(episodes):
            episode_num = str(i + 1).zfill(2)
            episode_name = f"{self.serie_name} s{season_number} {episode_num}.mp4"
            # Même format qu'avant : une entrée par domaine de la whitelist, dans le même ordre
            episode_urls = [ep_urls.get(domain, "none") for domain in self.whitelist]

            db.add_episode(
                path_name=self.path_name,
                series_name=self.serie_name,
                season_name=self.season_name,
                episode_list=(episode_name, "not_downloaded", episode_urls),
            )
