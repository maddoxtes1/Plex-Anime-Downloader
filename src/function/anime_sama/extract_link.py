import json
import re
from collections import Counter
from urllib.parse import urlparse
import logging

class extract_link:
    def __init__(self, episode_json, episode_js, logger):
        self.logger = logger
        whitelist = ['video.sibnet.ru', 'vidmoly.to', 'oneupload.to', 'sendvid.com']
        self.convert_json(episode_js, episode_json)

        self.update_domains(episode_json, whitelist)

        self.convert_data(episode_json, whitelist)

    def convert_json(self, episode_js, episode_json):
        with open(episode_js, "r", encoding="utf-8") as js_file:
            js_content = js_file.read()
        
        if js_content.strip().startswith("/*") and js_content.strip().endswith("*/"):
            self.logger.info(msg="Le fichier est un commentaire multi-ligne. Ignoré.")
            with open(episode_json, "w", encoding="utf-8") as json_file:
                json.dump({}, json_file, indent=4, ensure_ascii=False)
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

        with open(episode_json, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)


    def update_domains(self, episode_json, whitelist=None):
        if whitelist is None:
            whitelist = []
        
        with open(episode_json, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        
        def extract_domain(url):
            domain = urlparse(url).netloc
            return domain
        
        updates = []
        
        for var_name, eps in data.items():
            domains = [extract_domain(url) for url in eps.values()]
            
            domain_counts = Counter(domains)
            
            most_common_domain, most_common_count = domain_counts.most_common(1)[0]
            
            for key, url in eps.items():
                if extract_domain(url) != most_common_domain:
                    eps[key] = "none"
                
            updates.append((var_name, most_common_domain, eps))
            
        for old_var_name, most_common_domain, eps in updates:
            data[most_common_domain] = eps
            del data[old_var_name]  
                
        with open(episode_json, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
            
    def convert_data(self, episode_json, whitelist):
        with open(episode_json, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        
        combined_data = {}
        
        domain_urls = {domain: [] for domain in whitelist}
        
        for domain in whitelist:
            if domain in data:
                domain_urls[domain] = list(data[domain].values())
                
        max_length = max(len(urls) for urls in domain_urls.values())
        
        for i in range(max_length):
            combined_data[str(i + 1)] = [
                domain_urls[domain][i] if i < len(domain_urls[domain]) else "none"
                for domain in whitelist
            ]
        
        with open(episode_json, "w", encoding="utf-8") as json_file:
            json.dump(combined_data, json_file, indent=4, ensure_ascii=False)
