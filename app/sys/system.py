import os
import json
import re
import configparser
import logging
import time
from pathlib import Path
from typing import Union, Dict, List, Any, Optional

from .config import _ENV_CONFIG, _Folder_Config, _File_Config


class EnvConfig:
    """Classe pour gérer les variables d'environnement."""
    
    @staticmethod
    def _get_env_value(env_name: str) -> Any:
        """Récupère la valeur d'une variable d'environnement avec transformation si nécessaire."""
        if env_name not in _ENV_CONFIG:
            raise ValueError(f"L'environnement '{env_name}' n'est pas valide")
        
        config = _ENV_CONFIG[env_name]
        
        # Si use_default est True, utiliser directement la valeur par défaut
        if config.get("use_default", False):
            value = config["default"]
        else:
            # Sinon, chercher dans les variables d'environnement
            value = os.getenv(config["env_var"], config["default"])
        
        # Appliquer la transformation si elle existe (ex: pour les booléens)
        if "transform" in config:
            return config["transform"](value)
        
        # Convertir le type si nécessaire
        if config["type"] == bool:
            return value.lower() == "true"
        
        return config["type"](value)
    
    @classmethod
    def get_env(cls, env_name: Union[str, List[str]] = None) -> Union[Any, Dict[str, Any]]:
        """
        Récupère une ou plusieurs variables d'environnement.
    
    Args:
            env_name: Nom de la variable (str) ou liste de noms (List[str]).
                     Si None, retourne toutes les variables.
        
    Returns:
            - Si env_name est une string: retourne la valeur de la variable
            - Si env_name est une liste: retourne un dictionnaire {nom: valeur}
            - Si env_name est None: retourne toutes les variables dans un dictionnaire
        
        Examples:
            >>> EnvConfig.get_env("datapath")
            '/mnt/user/appdata/anime-downloader'
            
            >>> EnvConfig.get_env(["datapath", "plex_path"])
            {'datapath': '/mnt/user/appdata/anime-downloader', 'plex_path': '/mnt/user/appdata/plex'}
            
            >>> EnvConfig.get_env()  # Récupère toutes les variables
            {'datapath': ..., 'plex_path': ..., ...}
        """
        if env_name is None:
            # Retourner toutes les variables
            return {name: cls._get_env_value(name) for name in _ENV_CONFIG.keys()}
        elif isinstance(env_name, list):
            # Retourner plusieurs variables dans un dictionnaire
            return {name: cls._get_env_value(name) for name in env_name}
        else:
            # Retourner une seule variable (comportement original)
            return cls._get_env_value(env_name)

class FolderConfig:
    """Classe pour gérer les dossiers et fichiers de configuration."""
    
    _initialized = False  # Variable de classe pour tracker l'initialisation
    _initializing = False  # Variable de classe pour tracker si on est en train d'initialiser
    
    @staticmethod
    def _replace_variables(path: str) -> str:
        """Remplace les variables dans le chemin (ex: ;datapath;) par leur valeur."""
        result = path
        # Chercher les variables au format ;nom_variable;
        pattern = r';(\w+);'
        matches = re.findall(pattern, result)
        
        for var_name in matches:
            var_value = EnvConfig.get_env(var_name)
            result = result.replace(f';{var_name};', str(var_value))
        
        return result
    
    @classmethod
    def _get_folder_path(cls, folder_name: str) -> Optional[Path]:
        """Retourne le chemin résolu d'un dossier."""
        if folder_name not in _Folder_Config:
            return None
        
        folder_config = _Folder_Config[folder_name]
        path_str = folder_config["path"]
        resolved_path = cls._replace_variables(path_str)
        return Path(resolved_path)
    
    @classmethod
    def _create_folder(cls, folder_path: Path) -> bool:
        """Crée un dossier s'il n'existe pas."""
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False
    
    @classmethod
    def _get_file_default_content(cls, file_name: str) -> Optional[Any]:
        """Récupère le contenu par défaut d'un fichier depuis _File_Config."""
        if file_name not in _File_Config:
            return None
        
        file_config = _File_Config[file_name]
        return file_config.get("default")
    
    @classmethod
    def _get_file_type(cls, file_name: str) -> str:
        """Récupère le type d'un fichier depuis _File_Config."""
        if file_name not in _File_Config:
            return "text"
        
        file_config = _File_Config[file_name]
        return file_config.get("type", "text")
    
    @classmethod
    def _save_file_content(cls, file_path: Path, content: Any, file_type: str = "json") -> bool:
        """Sauvegarde le contenu dans un fichier selon son type."""
        try:
            if file_type == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=4, ensure_ascii=False)
            elif file_type == "configparser":
                # Pour configparser, on suppose que content est un dict
                config = configparser.ConfigParser()
                for section, options in content.items():
                    if section.startswith("_"):
                        continue  # Ignorer les clés qui commencent par _
                    config.add_section(section)
                    if isinstance(options, dict):
                        for key, value in options.items():
                            if not key.startswith("_"):
                                config.set(section, key, str(value))
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    config.write(f)
            elif file_type == "env":
                # Pour les fichiers .env, format KEY=value
                if isinstance(content, dict):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for key, value in content.items():
                            if not key.startswith("_"):
                                f.write(f"{key}={value}\n")
                else:
                    # Si ce n'est pas un dict, sauvegarder comme texte
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(str(content))
            else:
                # Type inconnu, sauvegarder comme texte
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            return True
        except Exception:
            return False
    
    @classmethod
    def _verify_file_integrity(cls, file_path: Path, file_name: str, default_content: str) -> bool:
        """Vérifie l'intégrité d'un fichier et le recrée si nécessaire."""
        # Si le fichier n'existe pas, il doit être créé
        if not file_path.exists():
            return False
        
        # Si default_content est "none", le fichier doit juste exister
        if default_content == "none":
            return True
        
        # Vérifier si le fichier peut être lu correctement selon son type
        try:
            file_type = cls._get_file_type(default_content)
            if file_type == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            elif file_type == "configparser":
                config = configparser.ConfigParser()
                config.read(file_path, encoding='utf-8')
            elif file_type == "env":
                # Pour les fichiers .env, vérifier qu'on peut le lire ligne par ligne
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            # Ligne valide trouvée
                            pass
            # Pour les autres types, on considère que si le fichier existe, c'est OK
            return True
        except Exception:
            # Le fichier est corrompu, il doit être recréé
            return False
    
    @classmethod
    def _replace_file_references(cls, value: str) -> str:
        """Remplace les références de fichiers au format :nom_fichier: par leur chemin complet."""
        result = value
        # Chercher les références de fichiers au format :nom_fichier:
        pattern = r':([^:]+):'
        matches = re.findall(pattern, result)
        
        for file_name in matches:
            # Trouver le chemin du fichier
            # Si on est en train d'initialiser, utiliser _find_path_without_init pour éviter la récursion
            file_path = cls.find_path(file_name=file_name)
            
            if file_path:
                result = result.replace(f':{file_name}:', str(file_path))
            else:
                # Si le fichier n'est pas trouvé, garder la référence originale
                pass
        
        return result

    
    @classmethod
    def _replace_variables_in_params(cls, params: Dict) -> Dict:
        """Remplace les variables et références de fichiers dans les paramètres des scripts."""
        if not params:
            return {}
        
        resolved_params = {}
        for key, value in params.items():
            if isinstance(value, str):
                # D'abord remplacer les références de fichiers au format :nom_fichier:
                resolved_value = cls._replace_file_references(value)
                # Ensuite remplacer les variables au format ;nom_variable;
                resolved_value = cls._replace_variables(resolved_value)
                resolved_params[key] = resolved_value
            else:
                # Si ce n'est pas une string, garder la valeur telle quelle
                resolved_params[key] = value
        
        return resolved_params
    
    @classmethod
    def _execute_file_script(cls, file_path: Path, script_name: str, script_params: Dict = None) -> bool:
        """
        Exécute un script associé à un fichier.
        
        Args:
            file_path: Chemin du fichier (utilisé seulement pour les logs et compatibilité)
            script_name: Nom du script à exécuter (ex: "create_plex_path")
            script_params: Paramètres à passer au script depuis file_script_params
        """
        try:
            # 1. Trouver la fonction du script dans le registre
            from .config import _FILE_SCRIPTS
            
            if script_name not in _FILE_SCRIPTS:
                return False
            
            script_func = _FILE_SCRIPTS[script_name]
            
            # 2. Remplacer les variables dans les paramètres
            #    Ex: ";plex_path;" → "/mnt/user/appdata/plex"
            #    Ex: ":plex_path.json:" → "/chemin/complet/plex_path.json"
            if script_params:
                resolved_params = cls._replace_variables_in_params(script_params)
            else:
                resolved_params = {}
            
            # 3. Exécuter le script avec les paramètres résolus
            #    Si des paramètres sont fournis, on les utilise (ex: plexpath_file, plexpath)
            #    Sinon, on passe file_path comme premier argument (pour compatibilité)
            if resolved_params:
                # Cas normal : utiliser les paramètres depuis file_script_params
                script_func(**resolved_params)
            else:
                # Cas de compatibilité : si aucun paramètre, passer file_path
                script_func(file_path)
            
            return True
        except Exception as e:
            # Logger l'erreur
            try:
                logger = universal_logger("FileScript", "file_scripts.log")
                logger.error(f"Erreur lors de l'exécution du script '{script_name}' pour {file_path}: {e}")
            except Exception:
                pass
            return False
    
    @classmethod
    def _create_file(cls, folder_path: Path, file_name: str, default_content: str, file_config: Dict = None, force_recreate: bool = False) -> bool:
        """Crée un fichier avec son contenu par défaut si nécessaire."""
        file_path = folder_path / file_name
        
        # Vérifier l'intégrité si le fichier existe déjà
        if file_path.exists() and not force_recreate:
            if cls._verify_file_integrity(file_path, file_name, default_content):
                # Fichier existe et est valide, exécuter le script après vérification
                if file_config and "file_script" in file_config:
                    script_params = file_config.get("file_script_params", {})
                    cls._execute_file_script(file_path, file_config["file_script"], script_params)
                return True
            # Le fichier est corrompu, on le supprime pour le recréer
            try:
                file_path.unlink()
            except Exception:
                pass
        
        # Si default_content est "none", créer un fichier vide
        if default_content == "none":
            try:
                file_path.touch()
                # Exécuter le script après création du fichier vide
                if file_config and "file_script" in file_config:
                    script_params = file_config.get("file_script_params", {})
                    cls._execute_file_script(file_path, file_config["file_script"], script_params)
                return True
            except Exception:
                return False
        
        # Sinon, récupérer le contenu par défaut depuis _File_Config
        content = cls._get_file_default_content(default_content)
        if content is None:
            # Si pas de contenu trouvé, créer un fichier vide
            try:
                file_path.touch()
                # Exécuter le script après création du fichier vide
                if file_config and "file_script" in file_config:
                    script_params = file_config.get("file_script_params", {})
                    cls._execute_file_script(file_path, file_config["file_script"], script_params)
                return True
            except Exception:
                return False
        
        # Déterminer le type de fichier
        file_type = cls._get_file_type(default_content)
        
        # Sauvegarder le contenu
        result = cls._save_file_content(file_path, content, file_type)
        
        # Exécuter le script après création du fichier
        if result and file_config and "file_script" in file_config:
            script_params = file_config.get("file_script_params", {})
            cls._execute_file_script(file_path, file_config["file_script"], script_params)
        
        return result
    
    @classmethod
    def _process_folder_recursive(cls, folder_config: Dict, base_path: Optional[Path] = None, folder_name: str = None) -> bool:
        """Traite récursivement un dossier et ses sous-dossiers."""
        try:
            # Si base_path n'est pas fourni, calculer depuis folder_name
            if base_path is None and folder_name:
                base_path = cls._get_folder_path(folder_name)
                if base_path is None:
                    return False
            
            if base_path is None:
                return False
            
            # Créer le dossier
            cls._create_folder(base_path)
            
            # Si c'est un dossier "normal", créer/vérifier les fichiers
            if folder_config.get("type") == "normal" and "file" in folder_config:
                for file_name, file_config in folder_config["file"].items():
                    default_content = file_config.get("default_content", "none")
                    cls._create_file(base_path, file_name, default_content, file_config)
            
            # Traiter les sous-dossiers s'ils existent
            if "folder" in folder_config:
                for sub_folder_name, sub_folder_config in folder_config["folder"].items():
                    # Résoudre le chemin du sous-dossier
                    sub_path_str = sub_folder_config.get("path", "")
                    if sub_path_str:
                        resolved_path = cls._replace_variables(sub_path_str)
                        sub_folder_path = Path(resolved_path)
                        # Traiter récursivement le sous-dossier
                        cls._process_folder_recursive(sub_folder_config, sub_folder_path, sub_folder_name)
            
            return True
        except Exception:
            return False
    
    @classmethod
    def init(cls) -> bool:
        """
        Initialise tous les dossiers et fichiers. Vérifie l'intégrité des fichiers et les recrée si nécessaire.
        
        Returns:
            True si l'initialisation a réussi
        """
        # Éviter d'initialiser plusieurs fois en même temps
        if cls._initializing:
            return True
        
        cls._initializing = True
        try:
            for folder_name, folder_config in _Folder_Config.items():
                cls._process_folder_recursive(folder_config, folder_name=folder_name)
            
            cls._initialized = True
            return True
        except Exception:
            return False
        finally:
            cls._initializing = False
    
    @classmethod
    def find_path(cls, folder_name: str = None, file_name: str = None) -> Optional[Path]:
        """
        Retourne le chemin d'un dossier ou d'un fichier.
        
        Args:
            folder_name: Nom du dossier (ex: "logs", "config", "database")
            file_name: Nom du fichier (seulement ceux définis dans config.py)
        
        Returns:
            Le chemin du dossier/fichier ou None si non trouvé
        
        Examples:
            >>> # Trouver un dossier
            >>> path = FolderConfig.find_path(folder_name="logs")
            >>> print(path)
            /mnt/user/appdata/plex-anime-downloader/logs
            
            >>> # Trouver un fichier
            >>> path = FolderConfig.find_path(file_name="config.conf")
            >>> print(path)
            /mnt/user/appdata/plex-anime-downloader/config/config.conf
        """
        # S'assurer que l'initialisation est faite
        if not cls._initialized:
            cls.init()
        
        # Si on cherche un fichier
        if file_name:
            # Chercher le fichier dans tous les dossiers "normal"
            for folder_name_search, folder_config in _Folder_Config.items():
                if folder_config.get("type") == "normal" and "file" in folder_config:
                    if file_name in folder_config["file"]:
                        folder_path = cls._get_folder_path(folder_name_search)
                        if folder_path is None:
                            continue
                        return folder_path / file_name
            return None
        
        # Si on cherche un dossier
        if folder_name:
            return cls._get_folder_path(folder_name)
        
        return None

class LoggerConfig:
    """Classe pour gérer la configuration des loggers."""
    
    _logs_path: Optional[Path] = None  # Variable de classe pour stocker le chemin des logs
    _log_level: int = logging.INFO  # Variable de classe pour stocker le niveau de log
    _initialized = False  # Variable de classe pour tracker l'initialisation
    
    @classmethod
    def _get_log_level_from_string(cls, level_str: str) -> int:
        """Convertit une chaîne de niveau de log en constante logging."""
        level_str = level_str.upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str, logging.INFO)
    
    @classmethod
    def _load_config_file(cls) -> Optional[Dict]:
        """Charge le fichier config.conf."""
        try:
            config_path = FolderConfig.find_path(file_name="config.conf")
            if config_path is None or not config_path.exists():
                return None
            
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            # Convertir en dict
            result = {}
            for section in config.sections():
                result[section] = dict(config.items(section))
            return result
        except Exception:
            return None
    
    @classmethod
    def init(cls) -> bool:
        """
        Initialise le chemin des logs et le niveau de log pour toute l'application.
        
        Returns:
            True si l'initialisation a réussi, False sinon
        """
        try:
            # Récupérer le chemin des logs
            logs_path = FolderConfig.find_path(folder_name="logs")
            if logs_path is None:
                raise ValueError("Le dossier 'logs' n'est pas configuré dans FolderConfig")
            cls._logs_path = logs_path
            
            # Charger le fichier config.conf pour récupérer le niveau de log
            config = cls._load_config_file()
            if config and "settings" in config:
                log_level_str = config["settings"].get("log_level", "INFO")
                cls._log_level = cls._get_log_level_from_string(log_level_str)
            
            cls._initialized = True
            return True
        except Exception:
            return False
    
    @classmethod
    def get_logs_path(cls) -> Optional[Path]:
        """
        Retourne le chemin des logs.
        
        Returns:
            Le chemin des logs ou None si non initialisé
        """
        return cls._logs_path
    
    @classmethod
    def get_log_level(cls) -> int:
        """
        Retourne le niveau de log configuré.
        
        Returns:
            Le niveau de log (constante logging)
        """
        return cls._log_level

def universal_logger(name="System", log_file="sys.log", path=None):
    """
    Crée un logger universel.
    
    Args:
        name: Nom du logger
        log_file: Nom du fichier de log
        path: Chemin du dossier de logs (optionnel, utilise LoggerConfig si None)
    
    Returns:
        Le logger configuré
    
    Examples:
        >>> # Après LoggerConfig.init()
        >>> logger = universal_logger("MyApp", "app.log")
    """
    # Si path n'est pas fourni, utiliser LoggerConfig
    if path is None:
        if not LoggerConfig._initialized:
            # Essayer d'initialiser automatiquement
            LoggerConfig.init()
        
        if LoggerConfig._logs_path is None:
            raise ValueError("LoggerConfig n'a pas été initialisé. Appelez LoggerConfig.init() d'abord.")
        path = str(LoggerConfig._logs_path)
    else:
        # Convertir en Path si c'est une string
        path = str(path)
    
    # Récupérer le niveau de log depuis LoggerConfig
    log_level = LoggerConfig.get_log_level()
    
    # Créer un nouveau logger
    logger = logging.getLogger(name)
    
    # Désactiver la propagation pour éviter les duplications
    logger.propagate = False
    
    # Si le logger a déjà des handlers, on ne fait rien
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(log_level)

    # S'assurer que le dossier existe
    Path(path).mkdir(parents=True, exist_ok=True)

    # Handler pour le fichier
    log_file_path = Path(path) / log_file
    file_handler = logging.FileHandler(str(log_file_path), encoding='utf-8')
    file_handler.setLevel(log_level)

    # Handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # Formatter pour les logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Ajouter les handlers au logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def _ping_news_server_loop():
    """Boucle interne pour le ping périodique vers le serveur d'actualités"""
    import requests
    import time
    import os
        
    while True:
        try:
            news_api_url = EnvConfig.get_env("news_api_url")
            if not news_api_url:
                time.sleep(300)  # Si pas d'URL, attendre 5 minutes avant de revérifier
                continue
                
            # Préparer les headers pour le tracking
            headers = {}
            # Lire Server_ID depuis .env
            try:
                env_file = FolderConfig.find_path(file_name=".env")
                if env_file and env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('Server_ID='):
                                server_id = line.split('=', 1)[1].strip()
                                if server_id and server_id != 'none':
                                    headers["X-Server-ID"] = server_id
                                break
            except Exception:
                pass
            # Lire Version depuis .env ou utiliser la version par défaut
            try:
                env_file = FolderConfig.find_path(file_name=".env")
                version = None
                if env_file and env_file.exists():
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith('Version='):
                                version = line.split('=', 1)[1].strip()
                                break
                if not version:
                    version = EnvConfig.get_env("plex_anime_downloader_V")
                if version:
                    headers["X-Server-Version"] = version
            except Exception:
                pass
                
            # Faire un ping simple (juste pour le tracking)
            try:
                requests.get(news_api_url, headers=headers, timeout=3)
            except:
                pass  # Ignorer les erreurs de connexion
            
            # Attendre 5 minutes avant le prochain ping
            time.sleep(300)
                    
        except Exception as e:
            # En cas d'erreur, attendre 5 minutes avant de réessayer
            time.sleep(300)
            pass


def ping_news_server():
    """
    Démarre le thread de ping vers le serveur d'actualités.
    Vérifie d'abord si news est activé dans config.conf avant de démarrer le thread.
    Le thread vérifie ensuite périodiquement si news est activé.
    Si news = False, aucune requête n'est envoyée.
    """
    import threading
    import configparser
    
    # Vérifier si news est activé AVANT de démarrer le thread
    news_enabled = True
    try:
        config_path = FolderConfig.find_path(file_name="config.conf")
        if config_path and config_path.exists():
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(config_path, encoding='utf-8')
            if config.has_section('settings') and config.has_option('settings', 'news'):
                news_enabled = config.get('settings', 'news', fallback='True').lower() == 'true'
    except Exception:
        # En cas d'erreur de lecture, utiliser True par défaut
        pass
    
    # Démarrer le thread seulement si news est activé
    if news_enabled:
        ping_thread = threading.Thread(target=_ping_news_server_loop, daemon=True)
        ping_thread.start()
        logger = universal_logger("NewsPing", "sys.log")
        logger.info("Thread de ping automatique vers le serveur d'actualités démarré (toutes les 5 minutes)")
    else:
        logger = universal_logger("NewsPing", "sys.log")
        logger.info("Thread de ping non démarré : news est désactivé dans config.conf")


