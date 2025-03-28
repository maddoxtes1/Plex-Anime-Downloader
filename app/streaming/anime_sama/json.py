import re
from collections import Counter
from urllib.parse import urlparse

from ...sys.logger import universal_logger
from ...sys.database import database


def get_unistalled_episode(path_list):
    path_name, serie_name, season_name = path_list
    logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")

    db = database()

    episodes = db.get_episode(
        path_name=path_name,
        series_name=serie_name,
        season_name=season_name
    )

    new_entries = []
    for episode_name, episode_status, episode_url in episodes:
        if episode_status == "not_downloaded":
            new_entries.append((episode_name, episode_url))
    return new_entries

class extract_link:
    def __init__(self, path_list, episode_js):
        self.logger = universal_logger(name="Anime-sama", log_file="anime-sama.log")
        whitelist = ['video.sibnet.ru', 'vidmoly.to', 'oneupload.to', 'sendvid.com']

        path_name, serie_name, season_name = path_list

        db = database()
        db.add_series(path_name, serie_name)
        db.add_season(path_name, serie_name, season_name)   

        self.convert_js_to_urls(episode_js, whitelist, path_name, serie_name, season_name)

    def convert_js_to_urls(self, episode_js, whitelist, path_name, serie_name, season_name):
        with open(episode_js, "r", encoding="utf-8") as js_file:
            js_content = js_file.read()
        
        if js_content.strip().startswith("/*") and js_content.strip().endswith("*/"):
            self.logger.info(msg="Le fichier est un commentaire multi-ligne. Ignoré.")
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