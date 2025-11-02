import requests
import re
from urllib.parse import urlparse
from collections import Counter

from ...sys.logger import universal_logger
from ...sys.database import database


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