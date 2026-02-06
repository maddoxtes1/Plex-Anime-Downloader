"""
Module de migration pour gérer les changements de version automatiquement.
Système universel qui peut déplacer des valeurs entre fichiers, supprimer des fichiers, etc.
"""

import configparser
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


# Définition des migrations par version
# Format : {version: {description: "...", changes: [...]}}
_MIGRATIONS = {
    "Beta-0.6.4": {
        "description": "Migration vers Beta-0.6.4 - Déplacement server_id et version vers .env, réorganisation config.conf",
        "changes": [
            {
                "type": "move_value",
                "description": "Déplacer server_id de server_id.json vers .env",
                "source": {
                    "file": ";datapath;/database/server_id.json",
                    "type": "json",
                    "key": "server_id"
                },
                "target": {
                    "file": ".env",
                    "type": "env",
                    "key": "Server_ID"
                }
            },
            {
                "type": "move_value",
                "description": "Déplacer version de config.conf [app] vers .env",
                "source": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "app",
                    "key": "version"
                },
                "target": {
                    "file": ".env",
                    "type": "env",
                    "key": "Version"
                },
                "remove_from_source": True
            },
            {
                "type": "move_value",
                "description": "Déplacer theme de config.conf [ui] vers [settings]",
                "source": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "ui",
                    "key": "theme"
                },
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "settings",
                    "key": "theme"
                },
                "remove_from_source": True
            },
            {
                "type": "remove_section",
                "description": "Supprimer section [ui] vide après migration",
                "file": "config.conf",
                "section": "ui"
            },
            {
                "type": "remove_section",
                "description": "Supprimer section [app] vide après migration",
                "file": "config.conf",
                "section": "app"
            },
            {
                "type": "delete_file",
                "description": "Supprimer server_id.json après migration",
                "file": ";datapath;/database/server_id.json"
            }
        ]
    },
    "Beta-0.6.5": {
        "description": "Migration vers Beta-0.6.5 - Ajout du paramètre as_Baseurl dans config.conf",
        "changes": [
            {
                "type": "add_key",
                "description": "Ajouter as_Baseurl dans la section scan-option de config.conf",
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "scan-option",
                    "key": "as_Baseurl"
                },
                "default_value": "https://anime-sama.tv"
            }
        ]
    },
    "Beta-0.7.0": {
        "description": "Migration vers Beta-0.7.0 - Ajout de plex_path.json",
        "changes": [
            {
                "type": "create_file",
                "description": "Créer le fichier planning_scan_data.json",
                "target": {
                    "file": ";datapath;/database/planning_scan_data.json",
                    "type": "json",
                    "default_content": "planning_scan_data.json"
                },
            },
            {
                "type": "add_section",
                "description": "Ajout de la section anime_sama de config.conf",
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "anime_sama"
                }
            },
            {
                "type": "add_key",
                "description": "Ajout de base_url dans la section anime_sama de config.conf",
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "anime_sama",
                    "key": "base_url"
                },
                "default_value": "https://anime-sama.tv"
            },
            {
                "type": "add_key",
                "description": "Ajout de auto_planning dans la section anime_sama de config.conf",
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "anime_sama",
                    "key": "auto_planning"
                },
                "default_value": "True"
            },
            {
                "type": "move_value",
                "description": "Déplacer as_Baseurl de la section scan-option vers la section anime_sama de config.conf",
                "source": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "scan-option",
                    "key": "as_Baseurl"
                },
                "target": {
                    "file": "config.conf",
                    "type": "configparser",
                    "section": "anime_sama",
                    "key": "base_url"
                },
                "remove_from_source": True
            }
        ]
    }
}


def _read_json_file(file_path: Path) -> Optional[Dict]:
    """Lit un fichier JSON."""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _write_json_file(file_path: Path, data: Dict):
    """Écrit un fichier JSON."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def _read_env_file(file_path: Path) -> Dict[str, str]:
    """Lit un fichier .env et retourne un dictionnaire."""
    env_vars = {}
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    except Exception:
        pass
    return env_vars


def _write_env_file(file_path: Path, env_vars: Dict[str, str]):
    """Écrit un fichier .env."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
    except Exception:
        pass


def _read_config_file(file_path: Path) -> Optional[configparser.ConfigParser]:
    """Lit un fichier config.conf."""
    try:
        if file_path.exists():
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(file_path, encoding='utf-8')
            return config
    except Exception:
        pass
    return None


def _write_config_file(file_path: Path, config: configparser.ConfigParser):
    """Écrit un fichier config.conf."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception:
        pass


def _resolve_file_path_with_env(file_name_or_path: str, base_path: Optional[Path] = None) -> Optional[Path]:
    """
    Résout un chemin de fichier en remplaçant les variables d'environnement.
    
    Args:
        file_name_or_path: Nom de fichier ou chemin (peut contenir ;variable;)
        base_path: Chemin de base optionnel
    
    Returns:
        Path résolu ou None
    """
    import re
    from .system import FolderConfig, EnvConfig
    
    if not file_name_or_path:
        return None
    
    # Remplacer les variables au format ;nom_variable;
    resolved_path = file_name_or_path
    pattern = r';(\w+);'
    matches = re.findall(pattern, resolved_path)
    
    for var_name in matches:
        try:
            var_value = EnvConfig.get_env(var_name)
            resolved_path = resolved_path.replace(f';{var_name};', str(var_value))
        except Exception:
            # Si la variable n'existe pas, garder le chemin tel quel
            pass
    
    # Si c'est un chemin absolu ou relatif avec séparateurs
    if os.sep in resolved_path or (os.altsep and os.altsep in resolved_path):
        file_path = Path(resolved_path)
        if file_path.is_absolute() and file_path.exists():
            return file_path
        # Si c'est un chemin relatif, essayer avec base_path
        if base_path:
            file_path = base_path / resolved_path
            if file_path.exists():
                return file_path
            return (base_path / resolved_path).resolve()
        return Path(resolved_path).resolve()
    
    # Sinon, c'est juste un nom de fichier - utiliser FolderConfig
    file_path = FolderConfig.find_path(file_name=resolved_path)
    if file_path:
        return file_path
    
    # Essayer avec le chemin de base
    if base_path:
        file_path = base_path / resolved_path
        if file_path.exists():
            return file_path
    
    return None


def _get_value_from_source(source: Dict, base_path: Path) -> Optional[str]:
    """
    Récupère une valeur depuis un fichier source.
    
    Args:
        source: Dictionnaire avec file, type, section (optionnel), key
        base_path: Chemin de base pour trouver les fichiers
    
    Returns:
        La valeur trouvée ou None
    """
    file_name_or_path = source.get("file")
    file_type = source.get("type")
    key = source.get("key")
    section = source.get("section")
    
    if not file_name_or_path or not file_type or not key:
        return None
    
    # Résoudre le chemin du fichier (avec variables d'environnement)
    file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
    if not file_path or not file_path.exists():
        return None
    
    # Lire selon le type
    if file_type == "json":
        data = _read_json_file(file_path)
        if data and isinstance(data, dict):
            return data.get(key)
    
    elif file_type == "configparser":
        config = _read_config_file(file_path)
        if config:
            if section:
                if config.has_section(section) and config.has_option(section, key):
                    return config.get(section, key)
            else:
                # Chercher dans toutes les sections
                for sec in config.sections():
                    if config.has_option(sec, key):
                        return config.get(sec, key)
    
    elif file_type == "env":
        env_vars = _read_env_file(file_path)
        return env_vars.get(key)
    
    return None


def _set_value_to_target(target: Dict, value: str, base_path: Path) -> bool:
    """
    Écrit une valeur dans un fichier cible.
    
    Args:
        target: Dictionnaire avec file, type, section (optionnel), key
        value: Valeur à écrire
        base_path: Chemin de base pour trouver les fichiers
    
    Returns:
        True si l'écriture a réussi
    """
    file_name_or_path = target.get("file")
    file_type = target.get("type")
    key = target.get("key")
    section = target.get("section")
    
    if not file_name_or_path or not file_type or not key:
        return False
    
    # Résoudre le chemin du fichier (avec variables d'environnement)
    file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
    if not file_path:
        # Si le fichier n'existe pas, créer le chemin résolu
        import re
        from .system import EnvConfig
        
        resolved_path = file_name_or_path
        pattern = r';(\w+);'
        matches = re.findall(pattern, resolved_path)
        
        for var_name in matches:
            try:
                var_value = EnvConfig.get_env(var_name)
                resolved_path = resolved_path.replace(f';{var_name};', str(var_value))
            except Exception:
                pass
        
        if base_path:
            file_path = base_path / resolved_path
        else:
            file_path = Path(resolved_path)
    
    # Créer le dossier parent si nécessaire
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Écrire selon le type
    if file_type == "json":
        data = _read_json_file(file_path) or {}
        if not isinstance(data, dict):
            data = {}
        data[key] = value
        _write_json_file(file_path, data)
        return True
    
    elif file_type == "configparser":
        config = _read_config_file(file_path) or configparser.ConfigParser(allow_no_value=True)
        if section:
            if not config.has_section(section):
                config.add_section(section)
            config.set(section, key, value)
        else:
            # Si pas de section, utiliser "settings" par défaut
            if not config.has_section("settings"):
                config.add_section("settings")
            config.set("settings", key, value)
        _write_config_file(file_path, config)
        return True
    
    elif file_type == "env":
        env_vars = _read_env_file(file_path)
        env_vars[key] = value
        _write_env_file(file_path, env_vars)
        return True
    
    return False


def _remove_value_from_source(source: Dict, base_path: Path) -> bool:
    """
    Supprime une valeur depuis un fichier source après migration.
    
    Args:
        source: Dictionnaire avec file, type, section (optionnel), key
        base_path: Chemin de base pour trouver les fichiers
    
    Returns:
        True si la suppression a réussi
    """
    file_name_or_path = source.get("file")
    file_type = source.get("type")
    key = source.get("key")
    section = source.get("section")
    
    if not file_name_or_path or not file_type or not key:
        return False
    
    # Résoudre le chemin du fichier (avec variables d'environnement)
    file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
    if not file_path or not file_path.exists():
        return False
    
    # Supprimer selon le type
    if file_type == "json":
        data = _read_json_file(file_path)
        if data and isinstance(data, dict) and key in data:
            del data[key]
            _write_json_file(file_path, data)
            return True
    
    elif file_type == "configparser":
        config = _read_config_file(file_path)
        if config:
            if section:
                if config.has_section(section) and config.has_option(section, key):
                    config.remove_option(section, key)
                    _write_config_file(file_path, config)
                    return True
    
    elif file_type == "env":
        env_vars = _read_env_file(file_path)
        if key in env_vars:
            del env_vars[key]
            _write_env_file(file_path, env_vars)
            return True
    
    return False


def _get_migrations_between_versions(old_version: str, new_version: str) -> List[Dict]:
    """
    Récupère toutes les migrations entre deux versions.
    
    Args:
        old_version: Ancienne version
        new_version: Nouvelle version
    
    Returns:
        Liste des migrations à appliquer
    """
    migrations_to_apply = []
    
    # Extraire les numéros de version pour comparer
    def parse_version(version_str: str) -> tuple:
        try:
            # Enlever "Beta-" et split par "."
            parts = version_str.replace("Beta-", "").split(".")
            return tuple(int(p) for p in parts)
        except:
            return (0, 0, 0)
    
    old_ver = parse_version(old_version)
    new_ver = parse_version(new_version)
    
    # Si la nouvelle version est plus récente, appliquer toutes les migrations entre les deux
    if new_ver > old_ver:
        for version, migration_data in _MIGRATIONS.items():
            mig_ver = parse_version(version)
            if old_ver < mig_ver <= new_ver:
                migrations_to_apply.append(migration_data)
    
    return migrations_to_apply


def _migrate_config_conf_rename(config_path: Path, change: Dict) -> bool:
    """Applique un renommage de clé dans config.conf."""
    if not config_path.exists():
        return False
    
    config = _read_config_file(config_path)
    if not config:
        return False
    
    change_type = change.get("type")
    section = change.get("section")
    old_key = change.get("old_key")
    new_key = change.get("new_key")
    
    if change_type == "rename_key" and section and old_key and new_key:
        if config.has_section(section) and config.has_option(section, old_key):
            value = config.get(section, old_key)
            config.remove_option(section, old_key)
            config.set(section, new_key, value)
            _write_config_file(config_path, config)
            return True
    
    return False


def run_migration(env_file=None, old_version=None, new_version=None):
    """
    Exécute les migrations nécessaires lors d'un changement de version.
    
    Args:
        env_file: Chemin du fichier .env
        old_version: Ancienne version
        new_version: Nouvelle version
    """
    if not old_version or not new_version:
        return []
    
    try:
        from .system import universal_logger, FolderConfig
        logger = universal_logger("Migration", "migration.log")
        logger.info(f"Début de la migration de {old_version} vers {new_version}")
    except Exception:
        logger = None
    
    # Récupérer les migrations à appliquer
    migrations = _get_migrations_between_versions(old_version, new_version)
    
    if not migrations:
        if logger:
            logger.info(f"Aucune migration nécessaire entre {old_version} et {new_version}")
        return []
    
    all_applied_changes = []
    base_path = Path(env_file).parent if env_file else None
    
    # Si pas de base_path, utiliser le chemin de config
    if not base_path:
        try:
            config_path = FolderConfig.find_path(file_name="config.conf")
            if config_path:
                base_path = config_path.parent
        except:
            pass
    
    # Appliquer chaque migration
    for migration in migrations:
        description = migration.get("description", "Migration")
        changes = migration.get("changes", [])
        
        if logger:
            logger.info(f"Application de: {description}")
        
        for change in changes:
            change_type = change.get("type")
            change_desc = change.get("description", "Changement")
            
            try:
                if change_type == "move_value":
                    # Déplacer une valeur d'un fichier à un autre
                    source = change.get("source")
                    target = change.get("target")
                    
                    if source and target:
                        # Récupérer la valeur depuis la source
                        value = _get_value_from_source(source, base_path)
                        
                        if value:
                            # Écrire dans la cible
                            if _set_value_to_target(target, value, base_path):
                                all_applied_changes.append(change_desc)
                                if logger:
                                    logger.info(f"  ✓ {change_desc}: '{value}' déplacé")
                                
                                # Par défaut, supprimer de la source après déplacement
                                # Sauf si remove_from_source est explicitement False
                                remove_from_source = change.get("remove_from_source", True)
                                if remove_from_source:
                                    _remove_value_from_source(source, base_path)
                                    if logger:
                                        logger.info(f"  ✓ Valeur supprimée de la source")
                        else:
                            if logger:
                                logger.warning(f"  ⚠ {change_desc}: valeur non trouvée dans la source")
                
                elif change_type == "delete_file":
                    # Supprimer un fichier
                    file_name_or_path = change.get("file")
                    if file_name_or_path:
                        file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
                        
                        if file_path and file_path.exists():
                            try:
                                file_path.unlink()
                                all_applied_changes.append(change_desc)
                                if logger:
                                    logger.info(f"  ✓ {change_desc}: fichier supprimé")
                            except Exception as e:
                                if logger:
                                    logger.error(f"  ✗ {change_desc}: erreur lors de la suppression - {e}")
                
                elif change_type == "rename_key":
                    # Renommer une clé dans un fichier
                    file_name_or_path = change.get("file")
                    if file_name_or_path:
                        file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
                        if file_path and file_path.exists():
                            if str(file_path).endswith('.conf'):
                                if _migrate_config_conf_rename(file_path, change):
                                    all_applied_changes.append(change_desc)
                                    if logger:
                                        logger.info(f"  ✓ {change_desc}")
                
                elif change_type == "remove_section":
                    # Supprimer une section entière d'un fichier
                    file_name_or_path = change.get("file")
                    section = change.get("section")
                    
                    if file_name_or_path and section:
                        file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
                        if file_path and file_path.exists():
                            if str(file_path).endswith('.conf'):
                                config = _read_config_file(file_path)
                                if config and config.has_section(section):
                                    # Vérifier si la section est vide
                                    if not config.items(section):
                                        config.remove_section(section)
                                        _write_config_file(file_path, config)
                                        all_applied_changes.append(change_desc)
                                        if logger:
                                            logger.info(f"  ✓ {change_desc}: section supprimée")
                                    else:
                                        if logger:
                                            logger.warning(f"  ⚠ {change_desc}: section non vide, ignorée")
                
                elif change_type == "add_key":
                    # Ajouter une nouvelle clé (seulement si elle n'existe pas déjà)
                    target = change.get("target") or change
                    default_value = change.get("default_value", "")
                    
                    # Vérifier si la clé existe déjà
                    file_name_or_path = target.get("file")
                    file_type = target.get("type")
                    key = target.get("key")
                    section = target.get("section")
                    
                    if file_name_or_path and file_type and key:
                        file_path = _resolve_file_path_with_env(file_name_or_path, base_path)
                        if file_path and file_path.exists():
                            if file_type == "configparser":
                                config = _read_config_file(file_path)
                                if config:
                                    if section and config.has_section(section) and config.has_option(section, key):
                                        # La clé existe déjà, ne pas l'ajouter
                                        if logger:
                                            logger.info(f"  ⚠ {change_desc}: clé déjà existante, ignorée")
                                        continue
                            elif file_type == "json":
                                data = _read_json_file(file_path)
                                if data and isinstance(data, dict) and key in data:
                                    # La clé existe déjà, ne pas l'ajouter
                                    if logger:
                                        logger.info(f"  ⚠ {change_desc}: clé déjà existante, ignorée")
                                    continue
                            elif file_type == "env":
                                env_vars = _read_env_file(file_path)
                                if key in env_vars:
                                    # La clé existe déjà, ne pas l'ajouter
                                    if logger:
                                        logger.info(f"  ⚠ {change_desc}: clé déjà existante, ignorée")
                                    continue
                    
                    # Ajouter la clé
                    if _set_value_to_target(target, default_value, base_path):
                        all_applied_changes.append(change_desc)
                        if logger:
                            logger.info(f"  ✓ {change_desc}")
                
                elif change_type == "no_change":
                    # Migration sans changement - juste pour marquer la version
                    all_applied_changes.append(change_desc)
                    if logger:
                        logger.info(f"  ✓ {change_desc}")
                
            except Exception as e:
                if logger:
                    logger.error(f"  ✗ Erreur lors de {change_desc}: {e}")
    
    # Résumé final
    if logger:
        if all_applied_changes:
            logger.info(f"Migration terminée: {len(all_applied_changes)} changement(s) appliqué(s)")
            logger.info("Résumé des changements:")
            for change_desc in all_applied_changes:
                logger.info(f"  - {change_desc}")
        else:
            logger.info("Aucun changement appliqué")
    
    return all_applied_changes
