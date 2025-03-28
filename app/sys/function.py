import os
from ..sys.logger import sys_logger
import json

_plex_path_json = None

def init_path(plex_path_json):
    global _plex_path_json
    _plex_path_json = plex_path_json

def get_path(langage):
    global _plex_path_json
    with open(_plex_path_json, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Filtrer les entrées qui ont 'path' et 'language'
    path_entries = [item for item in data if isinstance(item, dict) and 'path' in item and 'language' in item]
    
    # Chercher le premier dossier avec le langage spécifié
    found_paths = []
    for entry in path_entries:
        if langage in entry['language']:
            found_paths.append(entry['path'])
            
    if len(found_paths) > 1:
        logger = sys_logger()
        logger.warning(f"Plusieurs dossiers trouvés avec le langage '{langage}'. Utilisation du premier dossier: {found_paths[0]}")
        return found_paths[0]
    elif len(found_paths) == 1:
        return found_paths[0]
    else:
        return None

def create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)