import os 
import json
import configparser

from .function import create_path
from .logger import sys_logger
from .database import database

# Liste des versions connues/valides
KNOWN_VERSIONS = [
    "beta-0.6.3",
    # Ajoutez ici les nouvelles versions ici
]

# Version par défaut (dernière version stable)
DEFAULT_VERSION = "beta-0.6.3"


class check_sys:
    def __init__(self):
        self.data_path = os.getenv("DATA", "/mnt/user/appdata/anime-downloader")
        self.plex_path = os.getenv("PLEX", "/mnt/user/appdata/plex")
        self.app_secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-en-production")

        self.logs_path = os.path.join(self.data_path, "logs")
        create_path(path=self.logs_path)
        self.logger = sys_logger(path=self.logs_path)
        self.logger.info("Logs path Loaded/created")
        
        # Hash du mot de passe admin local (hashé à chaque démarrage)
        from werkzeug.security import generate_password_hash
        self.local_admin_password = os.getenv("LOCAL_ADMIN_PASSWORD", "change-moi")
        self.local_admin_password_hash = generate_password_hash(self.local_admin_password)
        self.logger.info("Mot de passe admin local hashé au démarrage")

        self.config_path = os.path.join(self.data_path, "config")
        create_path(path=self.config_path)
        self.logger.info("Config path Loaded/created")

        self.download_path = os.path.join(self.data_path, "download")
        create_path(path=self.download_path)
        create_path(path=os.path.join(self.download_path, "episode"))
        create_path(path=os.path.join(self.download_path, "json"))
        self.logger.info("Download path Loaded/created")

        self.database_path = os.path.join(self.data_path, "database")
        create_path(path=self.database_path)
        self.logger.info("Database path Loaded/created")

        # Générer ou charger le server_id unique
        self.server_id = self._get_or_create_server_id()
        self.logger.info(f"Server ID: {self.server_id}")

        self.logger.info("loading config")

        self.config = None
        self.anime_json = None
        self.plex_path_file = None
        self.plex_database = None
        self.scan_option_list = None
        self.threads = None
        self.timer = None
        self.theme = None
        self.version = None

        self.load_config()
        self.logger.info(f"file loaded: {self.config}, {self.anime_json}, {self.plex_path_file}, {self.plex_database}")

        

    def load_config(self):
        #config.conf
        config_file = f"{self.config_path}/config.conf"
        if not os.path.exists(config_file):
            config = configparser.ConfigParser(allow_no_value=True)
            config.add_section('settings')
            config.set('settings', 'threads', '4')
            config.set('settings', 'timer', '3600')
            config.add_section('scan-option')
            config.set('scan-option', 'anime-sama', 'True')
            config.set('scan-option', 'franime', 'False')
            config.add_section('ui')
            config.set('ui', 'theme', 'neon-cyberpunk')
            config.add_section('app')
            config.set('app', 'version', DEFAULT_VERSION)
            with open(config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            self.logger.info("Fichier de configuration créé")
        
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file, encoding='utf-8')
        
        self.threads = int(config.get('settings', 'threads'))
        self.timer = int(config.get('settings', 'timer'))
        self.scan_option_list = [bool(config['scan-option']['anime-sama']), bool(config['scan-option']['franime'])]
        
        # Gestion du thème
        if not config.has_section('ui'):
            config.add_section('ui')
            config.set('ui', 'theme', 'neon-cyberpunk')
            with open(config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        
        self.theme = config.get('ui', 'theme', fallback='neon-cyberpunk')
        
        # Gestion de la version
        if not config.has_section('app'):
            config.add_section('app')
            config.set('app', 'version', DEFAULT_VERSION)
            with open(config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        
        # Récupérer la version depuis config.conf
        config_version = config.get('app', 'version', fallback=DEFAULT_VERSION).strip()
        
        # Vérifier si la version est valide (dans la liste des versions connues)
        if config_version not in KNOWN_VERSIONS:
            # Version inconnue, utiliser la version par défaut
            self.logger.warning(f"Version inconnue '{config_version}' détectée dans config.conf. Utilisation de la version par défaut: {DEFAULT_VERSION}")
            config_version = DEFAULT_VERSION
            # Mettre à jour config.conf avec la version valide
            config.set('app', 'version', DEFAULT_VERSION)
            with open(config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        
        self.version = config_version
        self.logger.info(f"Version de l'application: {self.version}")
        
        self.config = config_file
        
        #anime.json
        anime_json = f"{self.config_path}/anime.json"
        if not os.path.exists(anime_json):
            data = [
                {
                    "auto_download": {
                        "lundi": [{"name": "none", "season": "none", "langage": "none", "streaming": "none", "file_name": "none"}],
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
            with open(anime_json, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
            self.logger.info("Fichier de configuration anime.json créé")
        
        self.anime_json = anime_json
        
        #plex_path.json
        # si le fichier plex_path.json n'existe pas, on le crée
        plex_path_file = f"{self.config_path}/plex_path.json"
        if not os.path.exists(plex_path_file):
            data_json = [
                {"_comment": "se fichier de configuration detecte automatiquement les dossier qui son present dans ton path plex"},
                {"_comment": "si tu vois pas de configuration assure toi de avoir mis le bon path et que dans se pas il aille des dossier"},
                {"_comment": "vous pouvez modifier le langage des dossier parcontre vous ne pouvez pas avoir un dossier qui a le même langage qu'un autre dossier"},
                {"_comment": "voci tout les langage possible pour le moment: vostfr, va, vf, vkr, vcn, vqc, vf1, vf2, vj,"},
                {"_comment": "vous etes pas obliger de metre tout les langage possible vous pouvez en metre que un ou deux"},
            ]
            with open(plex_path_file, 'w', encoding='utf-8') as json_file:
                json.dump(data_json, json_file, indent=4, ensure_ascii=False)
                self.logger.info("Fichier de configuration plex_path.json créé")
    
        # Lire le contenu existant du fichier plex_path.json
        with open(plex_path_file, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)

        # Filtrer les commentaires et les chemins
        comments = [item for item in existing_data if "_comment" in item]
        paths_data = [item for item in existing_data if "_comment" not in item]

        # Vérifier les dossiers existants et ne garder que ceux qui existent toujours
        updated_paths = []
        for item in paths_data:
            if item.get('path'):
                full_path = os.path.join(self.plex_path, item['path'])
                if os.path.exists(full_path) and os.path.isdir(full_path):
                    updated_paths.append(item)
                else:
                    self.logger.info(f"Dossier supprimé: {item['path']}")

        # Ajouter les nouveaux dossiers trouvés dans le répertoire
        existing_paths = [item['path'] for item in updated_paths]
        try:
            for item in os.listdir(self.plex_path):
                full_path = os.path.join(self.plex_path, item)
                if os.path.isdir(full_path) and item not in existing_paths:
                    updated_paths.append({"path": item, "language": ["disable"]})
                    self.logger.info(f"Nouveau dossier ajouté: {item}")
        except FileNotFoundError:
            self.logger.error(f"Le dossier {self.plex_path} n'existe pas")
            updated_paths = []

        # Reconstruire le fichier avec les commentaires et uniquement les chemins valides
        final_data = comments + updated_paths

        # Sauvegarder les modifications
        with open(plex_path_file, 'w', encoding='utf-8') as json_file:
            json.dump(final_data, json_file, indent=4, ensure_ascii=False)

        self.plex_path_file = plex_path_file

        #plex_database
        plex_database = f"{self.database_path}/plex_database.json"
        if not os.path.exists(plex_database):
            data_json = {}
            with open(plex_database, 'w', encoding='utf-8') as json_file:
                json.dump(data_json, json_file, indent=4, ensure_ascii=False)
            self.logger.info("Fichier de configuration plex_database.json créé")
        
        db = database(database_path=plex_database)

        with open(plex_path_file, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
        
        # Récupérer les chemins existants dans la base de données
        existing_paths = db.get_existing_path()
        
        # Supprimer les chemins qui n'existent plus dans plex_path.json
        paths_in_file = [item.get('path') for item in existing_data if item.get('path')]
        for path in existing_paths:
            if path not in paths_in_file:
                db.delete_path(path)
                self.logger.info(f"Chemin supprimé de la base de données: {path}")
        
        # Ajouter les nouveaux chemins
        for item in existing_data:
            if item.get('path') and item.get('language') != "disable" and not item.get("_comment"):
                if item.get('path') not in existing_paths:
                    db.add_path(path_name=item.get('path'))

        self.plex_database = plex_database

    def _get_or_create_server_id(self):
        """Génère ou récupère un identifiant unique pour ce serveur"""
        import uuid
        import json
        
        server_id_file = os.path.join(self.database_path, "server_id.json")
        
        try:
            if os.path.exists(server_id_file):
                with open(server_id_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("server_id", str(uuid.uuid4()))
            else:
                # Générer un nouveau server_id
                server_id = str(uuid.uuid4())
                with open(server_id_file, 'w', encoding='utf-8') as f:
                    json.dump({"server_id": server_id}, f, indent=2)
                return server_id
        except Exception as e:
            self.logger.warning(f"Erreur lors de la gestion du server_id: {e}, génération d'un nouveau")
            return str(uuid.uuid4())

