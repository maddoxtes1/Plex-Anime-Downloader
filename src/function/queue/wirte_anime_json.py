import logging
import json

class _wirte_in_anime_json:
    def __init__(self, number, url, anime_json):
        logger = logging.getLogger(f"{anime_json} | {number}:{url} ")
        try:
            with open(anime_json, 'r+', encoding='utf-8') as file:
                data = json.load(file)

            data[number] = url
            
            with open(anime_json, 'w') as file:
                json.dump(data, file, indent=4)
        except PermissionError as e:
            logger.warning(f"Erreur de permission : {e}")
        except FileNotFoundError as e:
            logger.error(f"Fichier non trouvé : {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON : {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")