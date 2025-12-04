"""
Fonctions utilitaires pour Flask (DB, config, etc.)
"""
import sqlite3
import os
import json
import configparser
from app.sys.logger import flask_logger


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
        self.log = flask_logger()
    
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Crée uniquement la DB users, pas les fichiers de config"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            conn = self.get_db_connection()
            with conn:
                conn.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    );
                    """
                )
            conn.close()
            self.log.info("Base users.db créée")

    def load_config_conf(self):
        """
        Lit config.conf et renvoie un dict avec threads, timer, anime_sama, franime.
        Ne crée pas le fichier : il doit déjà exister (créé par ton app Docker).
        """
        cfg = configparser.ConfigParser(allow_no_value=True)
        config_file = os.path.join(self.config_path, "config.conf")

        if not os.path.exists(config_file):
            # valeurs par défaut si le fichier n'existe pas
            return {
                "threads": 4,
                "timer": 3600,
                "anime_sama": True,
                "franime": False,
            }

        cfg.read(config_file, encoding="utf-8")
        threads = int(cfg.get("settings", "threads", fallback="4"))
        timer = int(cfg.get("settings", "timer", fallback="3600"))
        anime_sama = cfg.get("scan-option", "anime-sama", fallback="True").lower() == "true"
        franime = cfg.get("scan-option", "franime", fallback="False").lower() == "true"
        return {
            "threads": threads,
            "timer": timer,
            "anime_sama": anime_sama,
            "franime": franime,
        }

    def save_config_conf(self, threads: int, timer: int, anime_sama: bool, franime: bool):
        """
        Réécrit config.conf avec les nouvelles valeurs.
        """
        os.makedirs(self.config_path, exist_ok=True)
        config_file = os.path.join(self.config_path, "config.conf")
        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.add_section("settings")
        cfg.set("settings", "threads", str(threads))
        cfg.set("settings", "timer", str(timer))
        cfg.add_section("scan-option")
        cfg.set("scan-option", "anime-sama", "True" if anime_sama else "False")
        cfg.set("scan-option", "franime", "True" if franime else "False")
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

