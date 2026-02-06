import requests
import re
from urllib.parse import urlparse, urljoin
from collections import Counter
from bs4 import BeautifulSoup
from configparser import ConfigParser

from ...sys import universal_logger, FolderConfig
from ...sys.database import database


def extract_anime_info(name):
    """
    Extrait le titre et l'image d'une œuvre depuis une page anime-sama.
    
    Args:
        name: Nom de l'anime (ex: maou-no-musume-wa-yasashi-sugiru)
    
    Returns:
        dict: Dictionnaire avec 'titreOeuvre' et 'imgOeuvre', ou None en cas d'erreur
    """
    logger = universal_logger(name="Anime-sama - Extract Info", log_file="anime-sama.log")
    
    try:
        # Récupérer la configuration pour obtenir as_baseurl
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        
        # Construire l'URL à partir du name
        url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{name}/')
        logger.debug(f"Extraction des informations depuis: {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire le titre depuis <h4 id="titreOeuvre">
        titre_element = soup.find('h4', {'id': 'titreOeuvre'})
        titreOeuvre = None
        if titre_element:
            titreOeuvre = titre_element.get_text(strip=True)
        
        # Extraire l'image depuis <img id="coverOeuvre"> (pas imgOeuvre)
        img_element = soup.find('img', {'id': 'coverOeuvre'})
        imgOeuvre = None
        if img_element:
            imgOeuvre = img_element.get('src', '').strip()
        
        if not titreOeuvre or not imgOeuvre:
            logger.warning(f"Impossible d'extraire toutes les informations depuis {url} pour l'anime '{name}'")
            return None
        
        result = {
            'titreOeuvre': titreOeuvre,
            'imgOeuvre': imgOeuvre
        }
        
        logger.info(f"Informations extraites avec succès pour '{name}': {titreOeuvre}")
        return result
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion pour '{name}': {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour '{name}'")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête pour '{name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction pour '{name}': {e}")
        return None


def extract_anime_details(name):
    """
    Extrait les détails complets d'un anime depuis la page catalogue anime-sama.
    Inclut : titre, image, description, liste des saisons disponibles.
    
    Args:
        name: Nom de l'anime (ex: maou-no-musume-wa-yasashi-sugiru)
    
    Returns:
        dict: Dictionnaire avec 'title', 'image', 'description', 'seasons' (liste), ou None en cas d'erreur
    """
    logger = universal_logger(name="Anime-sama - Extract Details", log_file="anime-sama.log")
    
    try:
        # Récupérer la configuration pour obtenir as_baseurl
        config_path = FolderConfig.find_path(file_name="config.conf")
        config = ConfigParser(allow_no_value=True)
        config.read(config_path, encoding='utf-8')
        as_baseurl = config.get("anime_sama", "base_url", fallback="https://anime-sama.tv")
        
        # Construire l'URL à partir du name
        url = urljoin(as_baseurl.rstrip('/') + '/', f'catalogue/{name}/')
        logger.debug(f"Extraction des détails depuis: {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire le titre
        titre_element = soup.find('h4', {'id': 'titreOeuvre'})
        title = titre_element.get_text(strip=True) if titre_element else None
        
        # Extraire l'image
        img_element = soup.find('img', {'id': 'coverOeuvre'})
        image = img_element.get('src', '').strip() if img_element else None
        
        # Extraire la description
        # Chercher le h2 avec "Synopsis" et récupérer le paragraphe suivant
        description = None
        synopsis_h2 = soup.find('h2', string=re.compile(r'Synopsis', re.I))
        if synopsis_h2:
            # Chercher le paragraphe suivant avec la classe "text-sm text-gray-300 leading-relaxed"
            next_p = synopsis_h2.find_next('p', class_=re.compile(r'text-sm.*text-gray-300.*leading-relaxed', re.I))
            if next_p:
                description = next_p.get_text(strip=True)
            else:
                # Si pas trouvé avec la classe exacte, prendre le premier p après le h2
                next_p = synopsis_h2.find_next('p')
                if next_p:
                    description = next_p.get_text(strip=True)
        
        # Si pas trouvé via Synopsis, chercher dans d'autres endroits
        if not description:
            desc_elements = soup.find_all(['div', 'p'], class_=re.compile(r'description|synopsis|resume', re.I))
            if not desc_elements:
                desc_elements = soup.find_all(['div', 'p'], id=re.compile(r'description|synopsis|resume', re.I))
            if desc_elements:
                description = desc_elements[0].get_text(strip=True)
            else:
                # Chercher dans les paragraphes après le titre
                if titre_element:
                    next_p = titre_element.find_next('p')
                    if next_p:
                        description = next_p.get_text(strip=True)
        
        # Extraire les saisons disponibles
        # Chercher dans le div spécifique avec les classes "flex flex-wrap overflow-y-hidden justify-start bg-slate-900 bg-opacity-70 rounded mt-2 h-auto"
        seasons = []
        
        # Méthode 1: Chercher le div spécifique avec toutes les classes
        season_div = soup.find('div', class_=re.compile(r'flex.*flex-wrap.*overflow-y-hidden.*justify-start.*bg-slate-900', re.I))
        if not season_div:
            # Chercher avec moins de classes si la première méthode ne fonctionne pas
            season_div = soup.find('div', class_=re.compile(r'flex.*flex-wrap.*bg-slate-900', re.I))
        
        if season_div:
            # Chercher tous les liens <a> dans ce div qui ont un href avec "saison"
            season_links = season_div.find_all('a', href=re.compile(r'saison\d+'))
            for link in season_links:
                href = link.get('href', '')
                # Extraire le numéro de saison depuis l'URL (ex: "saison1/vostfr" -> "1", "saison1-2/vostfr" -> "1-2")
                season_match = re.search(r'saison(\d+(?:-\d+)?)', href, re.I)
                if season_match:
                    season_num = season_match.group(1)
                    if season_num not in seasons:
                        seasons.append(season_num)
            
            # Si pas de liens trouvés, chercher dans le script panneauAnime
            if not season_links:
                script_tags = season_div.find_all('script')
                for script in script_tags:
                    script_content = script.string or ''
                    # Chercher les appels panneauAnime("Saison X", "saisonY/...")
                    panneau_matches = re.findall(r'panneauAnime\([^,]+,\s*["\']saison(\d+(?:-\d+)?)', script_content, re.I)
                    for match in panneau_matches:
                        if match not in seasons:
                            seasons.append(match)
        
        # Méthode 2: Si pas trouvé, chercher dans tous les divs flex flex-wrap
        if not seasons:
            season_divs = soup.find_all('div', class_=re.compile(r'flex.*flex-wrap'))
            for div in season_divs:
                season_links = div.find_all('a', href=re.compile(r'saison\d+'))
                for link in season_links:
                    href = link.get('href', '')
                    season_match = re.search(r'saison(\d+(?:-\d+)?)', href, re.I)
                    if season_match:
                        season_num = season_match.group(1)
                        if season_num not in seasons:
                            seasons.append(season_num)
        
        # Méthode 3: Chercher dans tous les liens de la page qui pointent vers saison
        if not seasons:
            all_links = soup.find_all('a', href=re.compile(r'saison\d+'))
            for link in all_links:
                href = link.get('href', '')
                season_match = re.search(r'saison(\d+(?:-\d+)?)', href, re.I)
                if season_match:
                    season_num = season_match.group(1)
                    if season_num not in seasons:
                        seasons.append(season_num)
        
        # Trier les saisons numériquement
        def sort_season(s):
            if '-' in s:
                parts = s.split('-')
                return (int(parts[0]), int(parts[1]))
            return (int(s), 0)
        
        seasons.sort(key=sort_season)
        
        result = {
            'title': title,
            'image': image,
            'description': description or 'Description non disponible',
            'seasons': seasons,
            'seasons_count': len(seasons)
        }
        
        logger.info(f"Détails extraits avec succès pour '{name}': {len(seasons)} saison(s) trouvée(s)")
        return result
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion pour '{name}': {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Délai d'attente dépassé pour '{name}'")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la requête pour '{name}': {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction des détails pour '{name}': {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def get_planning_anime_urls():
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
        
        # Construire l'URL du planning
        planning_url = urljoin(as_baseurl.rstrip('/') + '/', 'planning/')
        logger.info(f"Récupération du planning depuis: {planning_url}")
        
        response = requests.get(planning_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
            logger.info(f"Jour {day_id}: {len(urls)} animes trouvés")
        
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
            logger.info(f"Jour 7 (no_day): {len(urls)} animes trouvés")
        else:
            planning_data["7"] = []
            logger.info("Jour 7 (no_day): div non trouvé")
        
        total_animes = sum(len(urls) for urls in planning_data.values())
        logger.info(f"Total: {total_animes} animes récupérés depuis le planning")
        
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

class extract_all_part_episode:
    def __init__(self, path_list, episode_js_list):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        whitelist = ['video.sibnet.ru', 'oneupload.to', 'vidmoly.to', 'sendvid.com']
        
        path_name, serie_name, season_name = path_list
        
        db = database()
        db.add_series(path_name, serie_name)
        db.add_season(path_name, serie_name, season_name)
        
        # Combiner tous les épisodes de tous les fichiers
        self.combine_all_episodes(episode_js_list, whitelist, path_name, serie_name, season_name)
    
    def convert_js_to_urls(self, episode_js, whitelist):
        """Extrait les URLs d'un fichier episode_js (même logique que extract_link)"""
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
                self.logger.info(msg=f"La variable {variable_name} est vide.")
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
        domain_urls = {domain: [] for domain in whitelist}
        
        for domain in whitelist:
            if domain in data_with_domains:
                domain_urls[domain] = list(data_with_domains[domain].values())
        
        return domain_urls
    
    def combine_all_episodes(self, episode_js_list, whitelist, path_name, serie_name, season_name):
        """Combine tous les épisodes de tous les fichiers avec une numérotation continue"""
        all_combined_urls = {domain: [] for domain in whitelist}
        
        # Extraire et combiner les URLs de tous les fichiers
        for episode_js in episode_js_list:
            domain_urls = self.convert_js_to_urls(episode_js, whitelist)
            if domain_urls is None:
                continue
            
            # Combiner les URLs de ce fichier avec celles déjà extraites
            for domain in whitelist:
                if domain_urls[domain]:
                    all_combined_urls[domain].extend(domain_urls[domain])
        
        # Trouver la longueur maximale (nombre total d'épisodes combinés)
        max_length = max(len(urls) for urls in all_combined_urls.values()) if any(all_combined_urls.values()) else 0
        
        if max_length == 0:
            self.logger.warning("Aucun épisode trouvé dans les fichiers")
            return
        
        # Ajouter tous les épisodes à la base de données avec numérotation continue
        db = database()
        for i in range(max_length):
            episode_num = str(i + 1).zfill(2)  # Numéro continue : 01, 02, 03, ... jusqu'à la fin
            season_number = season_name.replace("season", "").strip()
            episode_name = f"{serie_name} s{season_number} {episode_num}.mp4"
            episode_urls = [
                all_combined_urls[domain][i] if i < len(all_combined_urls[domain]) else "none"
                for domain in whitelist
            ]
            
            # Get current episode status
            episodes = db.get_episode(path_name, serie_name, season_name)
            current_status = "not_downloaded"
            
            if episode_name in episodes:
                current_status = episodes[episode_name]["status"]
                db.update_episode(
                    path_name=path_name,
                    series_name=serie_name,
                    season_name=season_name,
                    episode_list=(episode_name, current_status, episode_urls)
                )
            else:
                db.add_episode(
                    path_name=path_name,
                    series_name=serie_name,
                    season_name=season_name,
                    episode_list=(episode_name, current_status, episode_urls)
                )

class extract_link:
    def __init__(self, path_list, episode_js):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        whitelist = ['video.sibnet.ru', 'oneupload.to', 'vidmoly.to', 'sendvid.com']

        path_name, serie_name, season_name = path_list

        db = database()
        db.add_series(path_name, serie_name)
        db.add_season(path_name, serie_name, season_name)   

        self.convert_js_to_urls(episode_js, whitelist, path_name, serie_name, season_name)

    def convert_js_to_urls(self, episode_js, whitelist, path_name, serie_name, season_name):
        with open(episode_js, "r", encoding="utf-8") as js_file:
            js_content = js_file.read()
        
        if js_content.strip().startswith("/*") and js_content.strip().endswith("*/"):
            self.logger.debug(msg="Le fichier est un commentaire multi-ligne. Ignoré.")
            return
        
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
                self.logger.info(msg=f"La variable {variable_name} est vide.")
                continue
        
            numbered_urls = {str(i + 1): url for i, url in enumerate(urls_list)}
            data[variable_name] = numbered_urls

        if not data:
            self.logger.info(msg=f"le fichier.js est vide (surment a cause que l'anime est pas encore sortie)")
            return

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
        domain_urls = {domain: [] for domain in whitelist}
        
        for domain in whitelist:
            if domain in data_with_domains:
                domain_urls[domain] = list(data_with_domains[domain].values())
                
        max_length = max(len(urls) for urls in domain_urls.values())
        
        db = database()
        for i in range(max_length):
            episode_num = str(i + 1).zfill(2)
            season_number = season_name.replace("season", "").strip()
            episode_name = f"{serie_name} s{season_number} {episode_num}.mp4"
            episode_urls = [
                domain_urls[domain][i] if i < len(domain_urls[domain]) else "none"
                for domain in whitelist
            ]
            
            # Get current episode status
            episodes = db.get_episode(path_name, serie_name, season_name)
            current_status = "not_downloaded"
            
            if episode_name in episodes:
                current_status = episodes[episode_name]["status"]
                db.update_episode(
                    path_name=path_name,
                    series_name=serie_name,
                    season_name=season_name,
                    episode_list=(episode_name, current_status, episode_urls)
                )
            else:
                db.add_episode(
                    path_name=path_name,
                    series_name=serie_name,
                    season_name=season_name,
                    episode_list=(episode_name, current_status, episode_urls)
                )