_ENV_CONFIG = {
    "plex_anime_downloader_V": {
        "env_var": "PLEX_ANIME_DOWNLOADER_V",
        "default": "Beta-0.7.0",
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
    "news_api_url": {
        "env_var": "NEWS_API_URL",
        "default": "https://newspad.maddoxserv.com/api/news",
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
            "plex_database.json": {
                "default_content": "plex_database.json"
            },
            "users.db": {
                "default_content": "none",
                "file_script": "create_users_db",
                "file_script_params": {
                    "db_path": ":users.db:"
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
                    "database_path": ":plex_database.json:"
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
    "plex_database.json": {
        "type": "json",
        "default": {}
    },
    ".env": {
        "type": "env",
        "default": {
            "Version": "Beta-0.7.0",
            "Server_ID": "none",
        }
    },
    "config.conf": {
        "type": "configparser",
        "default": {
            "settings": {
                "threads": 4,
                "timer": 3600,
                "theme": "neon-cyberpunk",
                "news": "True",
                "log_level": "INFO"
            },
            "scan-option": {
                "anime-sama": True,
                "franime": False
            },
            "anime_sama": {
                "base_url": "https://anime-sama.tv",
                "auto_planning": True,
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


def create_users_db(db_path):
    """
    Initialise la base de données users.db.
    Vérifie si le fichier existe et s'il est valide, le crée ou le recrée si nécessaire.
    
    Args:
        db_path: Chemin complet vers le fichier users.db
        
    Returns:
        bool: True si l'initialisation a réussi, False sinon
    """
    import sqlite3
    import os
    from app.sys.system import universal_logger
    
    logger = universal_logger("UsersDB", "sys.log")
    
    # Créer le dossier parent si nécessaire
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Récupérer la définition SQL depuis _File_Config
    create_table_sql = _File_Config.get("users.db", {}).get("default", 
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);")
    
    # Ajouter "IF NOT EXISTS" si ce n'est pas déjà présent
    if "IF NOT EXISTS" not in create_table_sql.upper():
        create_table_sql = create_table_sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
    
    # Vérifier si le fichier existe et s'il est une base de données SQLite valide
    db_exists = os.path.exists(db_path)
    db_valid = False
    table_exists = False
    
    if db_exists:
        try:
            # Tenter de se connecter et de vérifier que c'est une base SQLite valide
            conn = sqlite3.connect(db_path)
            # Vérifier que la table users existe
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            table_exists = cursor.fetchone() is not None
            conn.close()
            db_valid = True
        except (sqlite3.DatabaseError, sqlite3.OperationalError):
            # Le fichier existe mais n'est pas une base de données valide
            db_valid = False
            try:
                os.remove(db_path)
                logger.warning("Fichier users.db corrompu, suppression et recréation")
            except Exception as e:
                logger.error(f"Impossible de supprimer le fichier users.db corrompu: {e}")
                return False
    
    # Créer la base de données et la table si nécessaire
    if not db_exists or not db_valid or not table_exists:
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            with conn:
                # Créer la table (IF NOT EXISTS garantit qu'elle ne sera pas recréée si elle existe)
                conn.execute(create_table_sql)
            conn.close()
            if not db_exists:
                logger.info("Base users.db créée avec la table users")
            elif not table_exists:
                logger.info("Table users créée dans users.db")
            else:
                logger.info("Base users.db recréée")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création de users.db: {e}")
            return False
    
    return True


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
    from app.sys.database import database

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
                full_path = os.path.join(plex_path, item)
                if os.path.isdir(full_path) and item not in existing_paths:
                    updated_paths.append({"path": item, "language": ["disable"]})
    except Exception:
        pass
    
    # Sauvegarder les modifications
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(updated_paths, json_file, indent=4, ensure_ascii=False)
    
    # Initialiser la base de données
    db = database(database_path=database_path)
    
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
        
        # Vérifier et générer le Server_ID si nécessaire
        current_server_id = env_vars.get('Server_ID', 'none')
        if current_server_id == "none" or not current_server_id:
            new_server_id = str(uuid.uuid4())
            env_vars['Server_ID'] = new_server_id
        
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
    "create_users_db": create_users_db
}