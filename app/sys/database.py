import json

from .system import universal_logger


class BaseDatabase:
    """
    Classe de base pour toutes les bases de données JSON.
    Contient les méthodes communes de lecture et sauvegarde.
    """
    def __init__(self, database_path, logger_name, allow_file_not_found=False):
        """
        Initialise la base de données.

        Args:
            database_path (str): Chemin vers le fichier JSON de la base de données
            logger_name (str): Nom du logger
            allow_file_not_found (bool): Si True, ne lève pas d'erreur si le fichier n'existe pas
        """
        if database_path is None:
            raise ValueError(f"Le chemin du fichier de base de données n'est pas défini pour {logger_name}")
        self.database_path = database_path
        self.logger = universal_logger(logger_name, "sys.log")
        self.allow_file_not_found = allow_file_not_found

    def _read_database(self):
        """
        Lit la base de données depuis le fichier JSON.

        Returns:
            dict: Les données de la base de données, ou {} si le fichier n'existe pas (si autorisé)

        Note:
            Le fichier utilisé est défini par self.database_path (initialisé dans __init__)
        """
        try:
            self.logger.debug(f"Lecture de la base de données depuis: {self.database_path}")
            with open(self.database_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                self.logger.debug(f"Base de données lue avec succès depuis: {self.database_path}")
                return data
        except FileNotFoundError:
            if self.allow_file_not_found:
                # Si le fichier n'existe pas et que c'est autorisé, retourner un dictionnaire vide
                self.logger.debug(f"Fichier '{self.database_path}' non trouvé, retour d'un dictionnaire vide")
                return {}
            raise
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture de la base de données depuis '{self.database_path}': {e}")
            return {}

    def save_database(self, data):
        """
        Sauvegarde la base de données dans le fichier JSON.

        Args:
            data: Les données à sauvegarder (dict)

        Note:
            Le fichier utilisé est défini par self.database_path (initialisé dans __init__)
        """
        try:
            self.logger.debug(f"Sauvegarde de la base de données dans: {self.database_path}")
            with open(self.database_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
            self.logger.debug(f"Base de données sauvegardée avec succès dans: {self.database_path}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la base de données dans '{self.database_path}': {e}")


class anime_data_database(BaseDatabase):
    """
    Base de données pour stocker les données des animes (séries, saisons, épisodes).
    Gère la structure hiérarchique : path -> series -> season -> episodes
    """
    anime_data_path = None

    def __init__(self, database_path=None):
        global anime_data_path
        if database_path is not None:
            anime_data_path = database_path
        if anime_data_path is None:
            raise ValueError("Le chemin du fichier de base de données anime-data n'est pas défini")
        super().__init__(anime_data_path, "AnimeDataDatabase", allow_file_not_found=False)

    def _verify_path(self, data, path_name):
        """
        Vérifie si un chemin (path) existe dans la base de données.

        Args:
            data (dict): Les données de la base de données
            path_name (str): Le nom du chemin à vérifier

        Returns:
            bool: True si le chemin existe, False sinon
        """
        if path_name not in data:
            self.logger.error(f"Le chemin '{path_name}' n'existe pas dans la base de données")
            return False
        return True

    def _verify_series(self, data, path_name, series_name):
        """
        Vérifie si une série existe dans un chemin donné.
        Vérifie d'abord que le chemin existe, puis que la série existe dans ce chemin.

        Args:
            data (dict): Les données de la base de données
            path_name (str): Le nom du chemin
            series_name (str): Le nom de la série à vérifier

        Returns:
            bool: True si la série existe dans le chemin, False sinon
        """
        if not self._verify_path(data, path_name):
            return False
        if series_name not in data[path_name]:
            self.logger.error(f"La série '{series_name}' n'existe pas dans le chemin '{path_name}'")
            return False
        return True

    def _verify_season(self, data, path_name, series_name, season_name):
        """
        Vérifie si une saison existe dans une série donnée.
        Vérifie d'abord que le chemin et la série existent, puis que la saison existe.

        Args:
            data (dict): Les données de la base de données
            path_name (str): Le nom du chemin
            series_name (str): Le nom de la série
            season_name (str): Le nom de la saison à vérifier

        Returns:
            bool: True si la saison existe dans la série, False sinon
        """
        if not self._verify_series(data, path_name, series_name):
            return False
        if season_name not in data[path_name][series_name]:
            self.logger.error(f"La saison '{season_name}' n'existe pas dans la série '{series_name}' dans le chemin '{path_name}'")
            return False
        return True

    def get_existing_path(self):
        """
        Récupère la liste de tous les chemins (paths) existants dans la base de données.

        Returns:
            list: Liste des noms de chemins
        """
        data = self._read_database()
        return list(data.keys())

    def add_path(self, path_name):
        """
        Ajoute un nouveau chemin (path) dans la base de données.
        Si le chemin existe déjà, ne fait rien.

        Args:
            path_name (str): Le nom du chemin à ajouter
        """
        data = self._read_database()
        if path_name not in data:
            data[path_name] = {}
            self.save_database(data)
            self.logger.debug(f"Chemin '{path_name}' ajouté avec succès")

    def delete_path(self, path_name):
        """
        Supprime un chemin (path) et tout son contenu (séries, saisons, épisodes) de la base de données.

        Args:
            path_name (str): Le nom du chemin à supprimer
        """
        data = self._read_database()
        if path_name in data:
            del data[path_name]
            self.save_database(data)
            self.logger.debug(f"Chemin '{path_name}' supprimé avec succès")

    def add_series(self, path_name, series_name):
        """
        Ajoute une nouvelle série dans un chemin donné.
        Vérifie d'abord que le chemin existe. Si la série existe déjà, ne fait rien.

        Args:
            path_name (str): Le nom du chemin où ajouter la série
            series_name (str): Le nom de la série à ajouter
        """
        data = self._read_database()
        if self._verify_path(data, path_name):
            if series_name not in data[path_name]:
                data[path_name][series_name] = {}
                self.save_database(data)
                self.logger.debug(f"Série '{series_name}' ajoutée avec succès dans le chemin '{path_name}'")

    def add_season(self, path_name, series_name, season_name):
        """
        Ajoute une nouvelle saison dans une série donnée.
        Vérifie d'abord que le chemin et la série existent. Si la saison existe déjà, ne fait rien.

        Args:
            path_name (str): Le nom du chemin
            series_name (str): Le nom de la série
            season_name (str): Le nom de la saison à ajouter
        """
        data = self._read_database()
        if self._verify_series(data, path_name, series_name):
            if season_name not in data[path_name][series_name]:
                data[path_name][series_name][season_name] = {}
                self.save_database(data)
                self.logger.debug(f"Saison '{season_name}' ajoutée avec succès dans la série '{series_name}' dans le chemin '{path_name}'")

    def add_episode(self, path_name, series_name, season_name, episode_list):
        """
        Ajoute un nouvel épisode dans une saison donnée.
        Vérifie d'abord que le chemin, la série et la saison existent.
        Si l'épisode existe déjà, ne fait rien.

        Args:
            path_name (str): Le nom du chemin
            series_name (str): Le nom de la série
            season_name (str): Le nom de la saison
            episode_list (tuple): Tuple contenant (episode_name, episode_status, episode_url)
                - episode_name (str): Le nom de l'épisode
                - episode_status (str): Le statut de l'épisode (ex: "not_downloaded", "downloaded")
                - episode_url (list): Liste des URLs de l'épisode pour chaque domaine
        """
        data = self._read_database()
        if self._verify_season(data, path_name, series_name, season_name):
            episode_name, episode_status, episode_url = episode_list
            if episode_name not in data[path_name][series_name][season_name]:
                data[path_name][series_name][season_name][episode_name] = {
                    "status": episode_status,
                    "url": episode_url
                }
            else:
                data[path_name][series_name][season_name][episode_name] = {
                    "status": episode_status,
                    "url": episode_url
                }
            self.save_database(data)
            self.logger.debug(f"Episode '{episode_name}' ajouté/modifier avec succès dans la saison '{season_name}' dans la série '{series_name}' dans le chemin '{path_name}'")

    def get_episode(self, path_name, series_name, season_name):
        """
        Récupère tous les épisodes d'une saison donnée.
        Vérifie d'abord que le chemin, la série et la saison existent.

        Args:
            path_name (str): Le nom du chemin
            series_name (str): Le nom de la série
            season_name (str): Le nom de la saison

        Returns:
            list: Liste de tuples (episode_name, episode_status, episode_url) pour chaque épisode
        """
        data = self._read_database()
        episodes = []
        if self._verify_season(data, path_name, series_name, season_name):
            for episode_name, episode_data in data[path_name][series_name][season_name].items():
                episodes.append((episode_name, episode_data["status"], episode_data["url"]))

        return episodes

    def get_unistalled_episode(self, path_list):
        """
        Récupère tous les épisodes non téléchargés (status = "not_downloaded") d'une saison.

        Args:
            path_list (tuple): Tuple contenant (path_name, series_name, season_name)

        Returns:
            list: Liste de tuples (episode_name, episode_url) pour les épisodes non téléchargés
        """
        path_name, series_name, season_name = path_list
        data = self._read_database()
        episodes = []
        if self._verify_season(data, path_name, series_name, season_name):
            for episode_name, episode_data in data[path_name][series_name][season_name].items():
                if episode_data["status"] == "not_downloaded":
                    episodes.append((episode_name, episode_data["url"]))
        return episodes


class anime_details_database(BaseDatabase):
    """
    Base de données pour stocker les détails des animes (titre, image, description, genres, saisons).
    Permet de mettre en cache les informations extraites depuis anime-sama pour éviter les requêtes HTTP répétées.

    Structure des données stockées:
        {
            "anime_name": {
                "title": str,
                "image": str,
                "description": str,
                "genres": list[str],
                "seasons": list[str],
                "seasons_count": int
            }
        }
    """
    _anime_details_path = None

    def __init__(self, database_path=None):
        global _anime_details_path
        if database_path is not None:
            _anime_details_path = database_path
        if _anime_details_path is None:
            raise ValueError("Le chemin du fichier de base de données anime-details n'est pas défini")
        super().__init__(_anime_details_path, "AnimeDetailsDatabase", allow_file_not_found=True)

    def get_anime_details(self, anime_name):
        """
        Récupère les détails d'un anime depuis la base de données.

        Args:
            anime_name (str): Nom de l'anime (ex: maou-no-musume-wa-yasashi-sugiru)

        Returns:
            dict: Dictionnaire avec 'title', 'image', 'description', 'genres', 'seasons', 'seasons_count',
                  ou None si l'anime n'est pas dans la base de données
        """
        data = self._read_database()
        if anime_name in data:
            self.logger.debug(f"Détails de '{anime_name}' trouvés dans le cache")
            return data[anime_name]
        return None

    def save_anime_details(self, anime_name, details):
        """
        Sauvegarde les détails d'un anime dans la base de données.

        Args:
            anime_name (str): Nom de l'anime
            details (dict): Dictionnaire contenant 'title', 'image', 'description', 'genres', 'seasons', 'seasons_count'
        """
        data = self._read_database()
        data[anime_name] = details
        self.save_database(data)
        self.logger.debug(f"Détails de '{anime_name}' sauvegardés dans le cache")

    def update_anime_details(self, anime_name, details):
        """
        Met à jour les détails d'un anime existant dans la base de données.

        Args:
            anime_name (str): Nom de l'anime
            details (dict): Dictionnaire contenant les nouvelles informations
        """
        data = self._read_database()
        if anime_name in data:
            data[anime_name].update(details)
            self.save_database(data)
            self.logger.debug(f"Détails de '{anime_name}' mis à jour dans le cache")
        else:
            self.logger.warning(f"Tentative de mise à jour de '{anime_name}' qui n'existe pas. Utilisation de save_anime_details.")
            self.save_anime_details(anime_name, details)

    def delete_anime_details(self, anime_name):
        """
        Supprime les détails d'un anime de la base de données.

        Args:
            anime_name (str): Nom de l'anime à supprimer
        """
        data = self._read_database()
        if anime_name in data:
            del data[anime_name]
            self.save_database(data)
            self.logger.debug(f"Détails de '{anime_name}' supprimés du cache")
        else:
            self.logger.warning(f"Tentative de suppression de '{anime_name}' qui n'existe pas dans le cache")

    def get_all_anime_names(self):
        """
        Récupère la liste de tous les noms d'anime dans la base de données.

        Returns:
            list: Liste des noms d'anime
        """
        data = self._read_database()
        return list(data.keys())

    def clear_cache(self):
        """Vide complètement le cache des détails d'anime"""
        data = {}
        self.save_database(data)
        self.logger.info("Cache des détails d'anime vidé")
