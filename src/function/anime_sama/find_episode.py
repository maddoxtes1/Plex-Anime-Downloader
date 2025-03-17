import logging
import requests
from bs4 import BeautifulSoup


class find_episode:
    def __init__(self, anime_info, episode_js):
        self.logger = logging.getLogger(f"anime: {anime_info[1]} saison {anime_info[2]}")

        self.anime_info = anime_info
        self.episode_js = episode_js
        self.is_download = self.execute()

    def execute(self):
        try:
            response = requests.get(self.anime_info[0])
            response.raise_for_status()
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                script_tag = soup.find('script', src=lambda x: x and 'episodes.js?' in x)
                
                if script_tag:
                    script_url = script_tag['src']
                    
                    if not script_url.startswith('http'):
                        script_url = self.anime_info[0].rstrip('/') + '/' + script_url.lstrip('/')
                        script_response = requests.get(url=script_url, stream=True)
                        
                        if script_response.status_code == 200:
                            with open(self.episode_js, 'wb') as file:
                                file.write(script_response.content)
                            return True
                else:
                    self.logger.warning(f"episode.js was not found: {script_url}")
                    return False
            else:
                self.logger.warning(f"url not work: {self.anime_info[0]}")
                return False
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Erreur de connexion : {e}")
            return False
        except requests.exceptions.Timeout:
            self.logger.error(f"Délai d'attente dépassé.")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur lors de la requête : {e}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur : {e}")
            return False