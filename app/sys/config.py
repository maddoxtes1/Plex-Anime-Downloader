_ENV_CONFIG = {
    "plex_anime_downloader_V": {
        "env_var": "PLEX_ANIME_DOWNLOADER_V",
        "default": "Beta-0.8.5",
        "type": str,
        "use_default": True
    },
    "datapath": {
        "env_var": "DATA_PATH",
        "default": "/mnt/user/appdata/plex-anime-downloader",
        "type": str
    },
    "plex_path": {
        "env_var": "PLEX_PATH",
        "default": "/mnt/user/appdata/plex",
        "type": str
    },
    "local_admin_password": {
        "env_var": "LOCAL_ADMIN_PASSWORD",
        "default": "change-moi",
        "type": str
    },
    "app_secret_key": {
        "env_var": "FLASK_SECRET_KEY",
        "default": "change-me-en-production",
        "type": str,
        "use_default": True
    },
    "use_waitress": {
        "env_var": "USE_WAITRESS",
        "default": "true",
        "type": bool,
        "transform": lambda x: x.lower() == "true"
    }
}

_Folder_Config = {
    "logs": {
        "path": ";datapath;/logs",
        "type": "ff"
    },
    "database": {
        "path": f";datapath;/database",
        "type": "normal",
        "file": {
            "anime_data.db": {
                "default_content": "none",
                "file_script": "create_anime_data_db",
                "file_script_params": {
                    "db_file": ":anime_data.db:"
                }
            },
            "anime_details.db": {
                "default_content": "none",
                "file_script": "create_anime_details_db",
                "file_script_params": {
                    "db_file": ":anime_details.db:"
                }
            },
            "planning_scan_data.json": {
                "default_content": "none"
            }
        }

    },
    "config": {
        "path": f";datapath;/config",
        "type": "normal",
        "file": {
            ".env": {
                "default_content": ".env",
                "file_script": "auto_env",
                "file_script_params": {
                    "env_file": ":.env:"
                }
            },
            "config.conf": {
                "default_content": "config.conf"
            },
            "plex_path.json": {
                "default_content": "none",
                "file_script": "create_plex_path",
                "file_script_params": {
                    "plexpath": ";plex_path;",
                    "plexpath_file": ":plex_path.json:",
                    "database_path": ":anime_data.db:"
                }
            },
            "anime.json": {
                "default_content": "anime.json"
            }
        }
    },
    "download": {
        "path": f";datapath;/download",
        "type": "ff",
        "folder": {
            "episode": {
                "path": f";datapath;/download/episode",
                "type": "ff"
            }
        }
    },
}

_File_Config = {
    ".env": {
        "type": "env",
        "default": {
            "Version": "Beta-0.8.2"
        }
    },
    "config.conf": {
        "type": "configparser",
        "default": {
            "settings": {
                "threads": 4,
                "timer": 3600,
                "theme": "neon-cyberpunk",
                "log_level": "INFO"
            },
            "flaresolver": {
                "host": "flaresolver",
                "port": 8191,
                "use_flaresolver": False,
            },
            "scan-option": {
                "anime-sama": True,
                "franime": False
            },
            "anime_sama": {
                "base_url": "https://anime-sama.tv",
                "auto_delete": True
            },
            "franime": {
                "base_url": "https://franime.fr",
                "api_base_url": "https://api.franime.fr",
                "auto_delete": True,
            }
            }
    },
    "anime.json": {
        "type": "json",
        "default": [{
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
                }]
    }
}

def _init_sqlite_database(db_file, db_class):
    """
    Initialise une base SQLite (création du fichier et des tables si besoin).
    La conversion des anciens fichiers JSON est gérée par migration.py (Beta-0.8.4).
    """
    if not db_file:
        return None

    return db_class(database_path=str(db_file))


def create_anime_data_db(db_file=None):
    """Script pour initialiser anime_data.db (et migrer anime_data.json si présent)."""
    from app.sys.database import anime_data_database
    _init_sqlite_database(db_file, anime_data_database)


def create_anime_details_db(db_file=None):
    """Script pour initialiser anime_details.db (et migrer anime_details.json si présent)."""
    from app.sys.database import anime_details_database
    _init_sqlite_database(db_file, anime_details_database)


def create_plex_path(plexpath_file=None, plexpath=None, database_path=None):
    """
    Script pour initialiser/mettre à jour plex_path.json.
    Détecte automatiquement les dossiers dans le répertoire Plex.
    Synchronise également avec plex_database.json.

    Args:
        plexpath_file: Chemin complet du fichier plex_path.json (Path)
        plexpath: Chemin du dossier Plex
    """
    import json
    import os
    from pathlib import Path
    # Import absolu pour éviter les problèmes de contexte d'exécution
    from app.sys.database import anime_data_database

    plex_path = plexpath
    file_path = Path(plexpath_file)


    # Lire le contenu existant du fichier (ou initialiser si vide/inexistant)
    existing_data = []
    if file_path.exists() and file_path.stat().st_size > 0:
        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                existing_data = json.load(json_file)
        except (json.JSONDecodeError, ValueError):
            # Si le fichier est corrompu, initialiser avec une liste vide
            existing_data = []

    # Filtrer les commentaires et récupérer les chemins
    paths_data = [item for item in existing_data if "_comment" not in item and isinstance(item, dict)]

    # Vérifier les dossiers existants et ne garder que ceux qui existent toujours
    updated_paths = []
    for item in paths_data:
        if item.get('path'):
            full_path = os.path.join(plex_path, item['path'])
            if os.path.exists(full_path) and os.path.isdir(full_path):
                updated_paths.append(item)

    # Ajouter les nouveaux dossiers trouvés dans le répertoire
    existing_paths = [item['path'] for item in updated_paths if item.get('path')]
    try:
        if plex_path and os.path.exists(plex_path) and os.path.isdir(plex_path):
            for item in os.listdir(plex_path):
                if item.startswith('.'):
                    continue
                full_path = os.path.join(plex_path, item)
                if os.path.isdir(full_path) and item not in existing_paths:
                    updated_paths.append({"path": item, "language": ["disable"]})
    except Exception:
        pass

    # Sauvegarder les modifications
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(updated_paths, json_file, indent=4, ensure_ascii=False)

    # Initialiser la base de données
    db = anime_data_database(database_path=database_path)

    # Récupérer les chemins existants dans la base de données
    existing_db_paths = db.get_existing_path()

    # Supprimer les chemins qui n'existent plus dans plex_path.json
    paths_in_file = [item.get('path') for item in updated_paths if item.get('path')]
    for path in existing_db_paths:
        if path not in paths_in_file:
            db.delete_path(path)

    # Ajouter les nouveaux chemins (uniquement ceux qui ne sont pas "disable")
    for item in updated_paths:
        if item.get('path') and not item.get("_comment"):
            language = item.get('language')
            # Vérifier que language n'est pas "disable" (string) ou ["disable"] (liste)
            if language != "disable" and language != ["disable"]:
                if item.get('path') not in existing_db_paths:
                    db.add_path(path_name=item.get('path'))


def auto_env(env_file=None):
    """
    Gère le Server_ID dans le fichier .env.
    Si Server_ID est "none", génère un nouveau UUID.
    Sinon, utilise celui qui existe déjà.
    À la fin, vérifie si la version a changé et lance un script de migration si nécessaire.
    """
    import uuid
    from pathlib import Path

    try:
        env_path = Path(env_file) if env_file else None

        if not env_path:
            return

        # Créer le fichier .env s'il n'existe pas
        if not env_path.exists():
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.touch()

        # Lire le fichier .env
        env_vars = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Ignorer les lignes vides et les commentaires
                    if not line or line.startswith('#'):
                        continue
                    # Parser les lignes KEY=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        # Récupérer la version actuelle depuis _ENV_CONFIG
        from .system import EnvConfig
        current_version = EnvConfig.get_env("plex_anime_downloader_V")

        # Récupérer la version dans le fichier .env
        env_version = env_vars.get('Version', '')

        # Vérifier si les versions sont différentes
        version_changed = False
        if env_version != current_version:
            version_changed = True
            # Mettre à jour la version dans le fichier
            env_vars['Version'] = current_version

        # Réécrire le fichier .env avec les modifications
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

        # Si la version a changé, lancer le script de migration
        if version_changed:
            try:
                # Importer et exécuter le script de migration depuis un autre fichier
                from .migration import run_migration
                run_migration(env_file=env_file, old_version=env_version, new_version=current_version)
            except ImportError:
                # Le fichier migration.py n'existe pas encore, on ignore
                pass
            except Exception:
                # En cas d'erreur, on continue
                pass
    except Exception:
        pass

_FILE_SCRIPTS = {
    "create_plex_path": create_plex_path,
    "auto_env": auto_env,
    "create_anime_data_db": create_anime_data_db,
    "create_anime_details_db": create_anime_details_db
}
