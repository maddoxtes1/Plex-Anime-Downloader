"""
Fonctions utilitaires pour Flask (DB, config, etc.)
"""
import sqlite3
import os
import json
import configparser
from pathlib import Path
from app.sys import universal_logger


class FlaskHelpers:
    """
    Classe contenant les fonctions utilitaires pour Flask.
    Les chemins sont injectés lors de l'initialisation.
    """
    
    def __init__(self, data_path: str, config_path: str, plex_root: str):
        self.data_path = data_path
        self.config_path = config_path
        self.plex_root = plex_root
        self.db_path = os.path.join(data_path, "database", "users.db")
        self.log = universal_logger("FlaskHelpers", "flask.log")
    
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load_config_conf(self):
        """
        Lit config.conf et renvoie un dict avec threads, timer, anime_sama, franime, news, log_level.
        Ne crée pas le fichier : il doit déjà exister (créé par ton app Docker).
        """
        from app.sys import FolderConfig
        from pathlib import Path
        
        # Utiliser FolderConfig pour trouver le chemin du fichier
        config_file = FolderConfig.find_path(file_name="config.conf")
        if not config_file:
            # Fallback sur l'ancien système si FolderConfig ne trouve pas le fichier
            config_file = Path(os.path.join(self.config_path, "config.conf"))
        else:
            config_file = Path(config_file)

        if not config_file.exists():
            # valeurs par défaut si le fichier n'existe pas
            return {
                "threads": 4,
                "timer": 3600,
                "anime_sama": True,
                "franime": False,
                "news": True,
                "log_level": "INFO",
            }

        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.read(config_file, encoding="utf-8")
        threads = int(cfg.get("settings", "threads", fallback="4"))
        timer = int(cfg.get("settings", "timer", fallback="3600"))
        anime_sama = cfg.get("scan-option", "anime-sama", fallback="True").lower() == "true"
        franime = cfg.get("scan-option", "franime", fallback="False").lower() == "true"
        news = cfg.get("settings", "news", fallback="True").lower() == "true"
        log_level = cfg.get("settings", "log_level", fallback="INFO")
        return {
            "threads": threads,
            "timer": timer,
            "anime_sama": anime_sama,
            "franime": franime,
            "news": news,
            "log_level": log_level,
        }

    def save_config_conf(self, threads: int, timer: int, anime_sama: bool, franime: bool, news: bool = None, log_level: str = None):
        """
        Met à jour config.conf avec les nouvelles valeurs en préservant les autres paramètres.
        """
        from app.sys import FolderConfig
        
        # Utiliser FolderConfig pour trouver le chemin du fichier
        config_file = FolderConfig.find_path(file_name="config.conf")
        if not config_file:
            # Fallback sur l'ancien système si FolderConfig ne trouve pas le fichier
            os.makedirs(self.config_path, exist_ok=True)
            config_file = Path(os.path.join(self.config_path, "config.conf"))
        else:
            config_file = Path(config_file)
        
        # Lire le fichier existant pour préserver tous les paramètres
        cfg = configparser.ConfigParser(allow_no_value=True)
        if config_file.exists():
            cfg.read(config_file, encoding="utf-8")
        
        # Créer les sections si elles n'existent pas
        if not cfg.has_section("settings"):
            cfg.add_section("settings")
        if not cfg.has_section("scan-option"):
            cfg.add_section("scan-option")
        
        # Mettre à jour les paramètres modifiés
        cfg.set("settings", "threads", str(threads))
        cfg.set("settings", "timer", str(timer))
        cfg.set("scan-option", "anime-sama", "True" if anime_sama else "False")
        cfg.set("scan-option", "franime", "True" if franime else "False")
        
        # Mettre à jour news si fourni
        if news is not None:
            cfg.set("settings", "news", "True" if news else "False")
        # Sinon, préserver la valeur existante ou utiliser la valeur par défaut
        elif not cfg.has_option("settings", "news"):
            cfg.set("settings", "news", "True")
        
        # Mettre à jour log_level si fourni
        if log_level is not None:
            cfg.set("settings", "log_level", log_level)
        # Sinon, préserver la valeur existante ou utiliser la valeur par défaut
        elif not cfg.has_option("settings", "log_level"):
            cfg.set("settings", "log_level", "INFO")
        
        # Préserver le thème s'il existe
        if not cfg.has_option("settings", "theme"):
            cfg.set("settings", "theme", "neon-cyberpunk")
        
        # Écrire le fichier
        with open(config_file, "w", encoding="utf-8") as f:
            cfg.write(f)

    def load_plex_paths(self):
        plex_path_file = os.path.join(self.config_path, "plex_path.json")
        if not os.path.exists(plex_path_file):
            return []
        with open(plex_path_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        result = []
        for item in data:
            path = item.get("path")
            if not path:
                continue
            languages = item.get("language") or []
            if isinstance(languages, str):
                languages = [languages]
            result.append({"path": path, "language": languages})
        return result

    def save_plex_paths(self, entries):
        plex_path_file = os.path.join(self.config_path, "plex_path.json")
        os.makedirs(self.config_path, exist_ok=True)
        with open(plex_path_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4, ensure_ascii=False)

    def get_user_by_username(self, username: str):
        conn = self.get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,),
        ).fetchone()
        conn.close()
        return user

    def save_user(self, username: str, password_hash: str):
        conn = self.get_db_connection()
        with conn:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password_hash),
            )
        conn.close()

    def load_anime_json(self):
        """Charge le fichier anime.json"""
        anime_json_path = os.path.join(self.config_path, "anime.json")
        with open(anime_json_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # Si erreur, retourner la structure par défaut
                return [
                    {
                        "auto_download": {
                            "lundi": [],
                            "mardi": [],
                            "mercredi": [],
                            "jeudi": [],
                            "vendredi": [],
                            "samedi": [],
                            "dimanche": [],
                            "no_day": []
                        },
                        "single_download": []
                    }
                ]

    def save_anime_json(self, data):
        """Sauvegarde le fichier anime.json"""
        anime_json_path = os.path.join(self.config_path, "anime.json")
        os.makedirs(self.config_path, exist_ok=True)
        with open(anime_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def add_anime_to_json(self, name, season, langage, streaming, file_name, day=None):
        """
        Ajoute un anime dans anime.json
        
        Args:
            name: Nom de l'anime (slug)
            season: Numéro de saison
            langage: Langage (vostfr, vf, etc.)
            streaming: Source de streaming (anime-sama, etc.)
            file_name: Nom de fichier (ou "none")
            day: Jour de la semaine (lundi, mardi, etc.) ou None pour single_download
        """
        data = self.load_anime_json()
        
        if not data or len(data) == 0:
            data = [
                {
                    "auto_download": {
                        "lundi": [],
                        "mardi": [],
                        "mercredi": [],
                        "jeudi": [],
                        "vendredi": [],
                        "samedi": [],
                        "dimanche": [],
                        "no_day": []
                    },
                    "single_download": []
                }
            ]
        
        anime_entry = {
            "name": name,
            "season": str(season),
            "langage": langage,
            "streaming": streaming,
            "file_name": file_name
        }
        
        # Vérifier si l'anime existe déjà
        if day and day in data[0]["auto_download"]:
            # Vérifier dans auto_download
            existing = data[0]["auto_download"][day]
            for item in existing:
                if item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage:
                    return False  # Déjà présent
            data[0]["auto_download"][day].append(anime_entry)
        else:
            # Ajouter dans single_download
            existing = data[0]["single_download"]
            for item in existing:
                if item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage:
                    return False  # Déjà présent
            data[0]["single_download"].append(anime_entry)
        
        self.save_anime_json(data)
        return True

    def check_anime_in_json(self, name, season, langage):
        """
        Vérifie si un anime existe dans anime.json
        
        Args:
            name: Nom de l'anime (slug)
            season: Numéro de saison
            langage: Langage (vostfr, vf, etc.)
        
        Returns:
            dict avec "exists": bool, "day": str ou None, "location": str
        """
        data = self.load_anime_json()
        
        if not data or len(data) == 0:
            return {"exists": False, "day": None, "location": None}
        
        # Chercher dans auto_download
        for day in ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche", "no_day"]:
            if day in data[0]["auto_download"]:
                for item in data[0]["auto_download"][day]:
                    if item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage:
                        return {"exists": True, "day": day if day != "no_day" else None, "location": f"auto_download.{day}"}
        
        # Chercher dans single_download
        if "single_download" in data[0]:
            for item in data[0]["single_download"]:
                if item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage:
                    return {"exists": True, "day": None, "location": "single_download"}
        
        return {"exists": False, "day": None, "location": None}

    def remove_anime_from_json(self, name, season, langage):
        """
        Supprime un anime de anime.json
        
        Args:
            name: Nom de l'anime (slug)
            season: Numéro de saison
            langage: Langage (vostfr, vf, etc.)
        
        Returns:
            bool: True si supprimé, False si non trouvé
        """
        data = self.load_anime_json()
        
        if not data or len(data) == 0:
            return False
        
        found = False
        
        # Chercher et supprimer dans auto_download
        for day in ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche", "no_day"]:
            if day in data[0]["auto_download"]:
                original_length = len(data[0]["auto_download"][day])
                data[0]["auto_download"][day] = [
                    item for item in data[0]["auto_download"][day]
                    if not (item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage)
                ]
                if len(data[0]["auto_download"][day]) < original_length:
                    found = True
        
        # Chercher et supprimer dans single_download
        if "single_download" in data[0]:
            original_length = len(data[0]["single_download"])
            data[0]["single_download"] = [
                item for item in data[0]["single_download"]
                if not (item.get("name") == name and item.get("season") == str(season) and item.get("langage") == langage)
            ]
            if len(data[0]["single_download"]) < original_length:
                found = True
        
        if found:
            self.save_anime_json(data)
        
        return found

