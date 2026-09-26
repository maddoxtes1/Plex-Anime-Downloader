"""
Fonctions utilitaires pour Flask (DB, config, etc.)
"""
import os
import json
import configparser
from app.sys import FolderConfig
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
        self.log = universal_logger("FlaskHelpers", "flask.log")

    def load_config_conf(self):
        """
        Lit config.conf et renvoie TOUS les paramètres depuis le fichier.
        Ne crée pas le fichier : il doit déjà exister (créé par ton app Docker).
        """

        # Utiliser FolderConfig pour trouver le chemin du fichier
        config_file = FolderConfig.find_path(file_name="config.conf")
        config_file = Path(config_file)
        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.read(config_file, encoding="utf-8")

        # Récupérer TOUS les sections et options
        all_params = {}
        for section in cfg.sections():
            for option in cfg.options(section):
                all_params[f"[{section}] {option}"] = cfg.get(section, option)

        # Retourner un dict structuré par section pour faciliter l'accès dans le template
        structured = {
            "settings": {
                "threads": cfg.get("settings", "threads", fallback="4"),
                "timer": cfg.get("settings", "timer", fallback="3600"),
                "log_level": cfg.get("settings", "log_level", fallback="INFO"),
                "theme": cfg.get("settings", "theme", fallback="neon-cyberpunk"),
            },
            "scan_option": {
                "anime_sama": cfg.get("scan-option", "anime-sama", fallback="False").lower() == "true",
                "franime": cfg.get("scan-option", "franime", fallback="False").lower() == "true",
            },
            "anime_sama": {
                "base_url": cfg.get("anime_sama", "base_url", fallback="https://anime-sama.tv"),
                "auto_delete": cfg.get("anime_sama", "auto_delete", fallback="True").lower() == "true",
            },
            "franime": {
                "base_url": cfg.get("franime", "base_url", fallback="https://franime.fr"),
                "api_base_url": cfg.get("franime", "api_base_url", fallback="https://api.franime.fr"),
                "auto_delete": cfg.get("franime", "auto_delete", fallback="True").lower() == "true",
            },
            "flaresolver": {
                "use_flaresolver": cfg.get("flaresolver", "use_flaresolver", fallback="False").lower() == "true",
                "host": cfg.get("flaresolver", "host", fallback="flaresolver"),
                "port": cfg.get("flaresolver", "port", fallback="8191"),
            },
            # Tous les autres paramètres bruts (section:key)
            "_brute": all_params,
        }

        return structured

    def save_config_conf(self, threads: int = None, timer: int = None, log_level: str = None, theme: str = None, anime_sama: bool = None, franime: bool = None, anime_sama_base_url: str = None, anime_sama_auto_delete: bool = None, franime_base_url: str = None, franime_api_base_url: str = None, franime_auto_delete: bool = None, use_flaresolver: bool = None, flaresolver_host: str = None, flaresolver_port: str = None):
        """
        Met à jour config.conf avec les nouvelles valeurs en préservant TOUS les autres paramètres.
        """

        config_file = FolderConfig.find_path(file_name="config.conf")
        config_file = Path(config_file)

        # LIRE TOUS les paramètres existants
        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.read(config_file, encoding="utf-8")

        # Sauvegarder toutes les sections et options existantes
        all_params = {}
        for section in cfg.sections():
            for option in cfg.options(section):
                all_params[f"[{section}] {option}"] = cfg.get(section, option)

        # Mettre à jour seulement les paramètres donnés
        updates_applied = False

        if threads is not None:
            cfg.set("settings", "threads", str(threads))
            updates_applied = True
        if timer is not None:
            cfg.set("settings", "timer", str(timer))
            updates_applied = True
        if log_level is not None:
            cfg.set("settings", "log_level", log_level)
            updates_applied = True
        if theme is not None:
            cfg.set("settings", "theme", theme)
            updates_applied = True

        if anime_sama is not None:
            cfg.set("scan-option", "anime-sama", "True" if anime_sama else "False")
            updates_applied = True
        if franime is not None:
            cfg.set("scan-option", "franime", "True" if franime else "False")
            updates_applied = True

        if anime_sama_base_url is not None:
            cfg.set("anime_sama", "base_url", anime_sama_base_url)
            updates_applied = True
        if anime_sama_auto_delete is not None:
            cfg.set("anime_sama", "auto_delete", "True" if anime_sama_auto_delete else "False")
            updates_applied = True

        if franime_base_url is not None:
            cfg.set("franime", "base_url", franime_base_url)
            updates_applied = True
        if franime_api_base_url is not None:
            cfg.set("franime", "api_base_url", franime_api_base_url)
            updates_applied = True
        if franime_auto_delete is not None:
            cfg.set("franime", "auto_delete", "True" if franime_auto_delete else "False")
            updates_applied = True

        if use_flaresolver is not None:
            cfg.set("flaresolver", "use_flaresolver", "True" if use_flaresolver else "False")
            updates_applied = True
        if flaresolver_host is not None:
            cfg.set("flaresolver", "host", flaresolver_host)
            updates_applied = True
        if flaresolver_port is not None:
            cfg.set("flaresolver", "port", str(flaresolver_port))
            updates_applied = True

        # Écrire le fichier avec TOUS les paramètres
        with open(config_file, "w", encoding="utf-8") as f:
            cfg.write(f)

        # Confirmation pour debugging
        self.log.info(f"✅ Config sauvegardée dans : {config_file}")
        if updates_applied:
            self.log.info(f"   ✅ {updates_applied} paramètres mis à jour")
        else:
            self.log.info(f"   ℹ️  Aucun paramètre à mettre à jour")



    def load_plex_paths(self) -> list:
        """
        Charge les chemins Plex depuis plex_path.json.

        Returns:
            list: Liste de dictionnaires {"path": str, "language": list[str]}
        """
        plex_path_file = Path(self.config_path) / "plex_path.json"
        if not plex_path_file.exists():
            return []

        try:
            with open(plex_path_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

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

    def save_plex_paths(self, entries: list):
        """
        Sauvegarde les chemins Plex dans plex_path.json.

        Args:
            entries: Liste de dictionnaires {"path": str, "language": list[str]}
        """
        plex_path_file = Path(self.config_path) / "plex_path.json"
        plex_path_file.parent.mkdir(parents=True, exist_ok=True)
        with open(plex_path_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4, ensure_ascii=False)

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
            "file_name": file_name,
            "day": day
        }
