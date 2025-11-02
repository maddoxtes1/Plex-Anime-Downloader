import os

from ...sys.logger import universal_logger
from ...sys.function import get_path
from ..api import find_episode, extract_link, extract_all_part_episode
from ...sys.database import database

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
        folder_name = get_path(langage=self.anime_langage)
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

    


