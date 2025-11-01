import json

from .logger import sys_logger


class database:
    _path = None
    def __init__(self, database_path=None):
        global _path
        if database_path is not None:
            _path = database_path
        if _path is None:
            raise ValueError("Le chemin du fichier de log n'est pas défini")
        self.database_path = _path
        self.logger = sys_logger()
    
    def _read_database(self):
        try:
            with open(self.database_path, 'r', encoding='utf-8') as json_file:
                return json.load(json_file)
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture de la base de données: {e}")
            return {}
    
    def save_database(self, data):
        try:
            with open(self.database_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la base de données: {e}")
    
    def _verify_path(self, data, path_name):
        if path_name not in data:
            self.logger.error(f"Le chemin '{path_name}' n'existe pas dans la base de données")
            return False
        return True
    
    def _verify_series(self, data, path_name, series_name):
        if not self._verify_path(data, path_name):
            return False
        if series_name not in data[path_name]:
            self.logger.error(f"La série '{series_name}' n'existe pas dans le chemin '{path_name}'")
            return False
        return True
    
    def _verify_season(self, data, path_name, series_name, season_name):
        if not self._verify_series(data, path_name, series_name):
            return False
        if season_name not in data[path_name][series_name]:
            self.logger.error(f"La saison '{season_name}' n'existe pas dans la série '{series_name}' dans le chemin '{path_name}'")
            return False
        return True
    
    def get_existing_path(self):
        data = self._read_database()
        return list(data.keys())

    def add_path(self, path_name):
        data = self._read_database()
        if path_name not in data:
            data[path_name] = {}
            self.save_database(data)
            self.logger.debug(f"Chemin '{path_name}' ajouté avec succès")
            
    def delete_path(self, path_name):
        data = self._read_database()
        if path_name in data:
            del data[path_name]
            self.save_database(data)
            self.logger.debug(f"Chemin '{path_name}' supprimé avec succès")

    def add_series(self, path_name, series_name):
        data = self._read_database()
        if self._verify_path(data, path_name):
            if series_name not in data[path_name]:
                data[path_name][series_name] = {}
                self.save_database(data)
                self.logger.debug(f"Série '{series_name}' ajoutée avec succès dans le chemin '{path_name}'")
    
    def add_season(self, path_name, series_name, season_name):
        data = self._read_database()
        if self._verify_series(data, path_name, series_name):
            if season_name not in data[path_name][series_name]:
                data[path_name][series_name][season_name] = {}
                self.save_database(data)
                self.logger.debug(f"Saison '{season_name}' ajoutée avec succès dans la série '{series_name}' dans le chemin '{path_name}'")
    
    def add_episode(self, path_name, series_name, season_name, episode_list):
        data = self._read_database()
        if self._verify_season(data, path_name, series_name, season_name):
            episode_name, episode_status, episode_url = episode_list
            if episode_name not in data[path_name][series_name][season_name]:
                data[path_name][series_name][season_name][episode_name] = {
                    "status": episode_status,
                    "url": episode_url
                }
                self.save_database(data)
                self.logger.debug(f"Episode '{episode_name}' ajouté avec succès dans la saison '{season_name}' dans la série '{series_name}' dans le chemin '{path_name}'")
    
    def update_episode(self, path_name, series_name, season_name, episode_list):
        data = self._read_database()
        episode_name, episode_status, episode_url = episode_list
        if self._verify_season(data, path_name, series_name, season_name):
            if episode_name not in data[path_name][series_name][season_name]:
                self.logger.error(f"L'épisode '{episode_name}' n'existe pas dans la saison '{season_name}' dans la série '{series_name}' dans le chemin '{path_name}'")
                return
            
            data[path_name][series_name][season_name][episode_name] = {
                "status": episode_status,
                "url": episode_url
            }
            self.save_database(data)    
            self.logger.debug(f"L'épisode '{episode_name}' a été mis à jour avec succès")
    
    def get_episode(self, path_name, series_name, season_name):
        data = self._read_database()
        episodes = []
        if self._verify_season(data, path_name, series_name, season_name):
            for episode_name, episode_data in data[path_name][series_name][season_name].items():
                episodes.append((episode_name, episode_data["status"], episode_data["url"]))
        return episodes
    
    def get_unistalled_episode(self, path_list):
        path_name, series_name, season_name = path_list
        data = self._read_database()
        episodes = []
        if self._verify_season(data, path_name, series_name, season_name):
            for episode_name, episode_data in data[path_name][series_name][season_name].items():
                if episode_data["status"] == "not_downloaded":
                    episodes.append((episode_name, episode_data["url"]))
        return episodes