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

