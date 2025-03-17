import src.function as Function
import os
import json
import time
import configparser
import logging

class check_sys_file:
    def __init__(self):
        self.data_path = os.getenv("DATA", "/mnt/user/appdata/anime-downloader")
        self.temp_path = os.getenv("TEMP", "/tmp/anime-downloader")
        self.plex_path = os.getenv("PLEX", "/mnt/user/appdata/plex")


        logs_path, config_path, anime_path, download_path, episode_path = self.check_path()
        Function.setup_logging(logs_path=logs_path)
        self.logger = logging.getLogger("Checking file:")
        self.logger.info(msg="folders was loaded")

        config, config_file, anime_json = self.check_file(config_path=config_path, anime_path=anime_path)
        self.logger.info(msg="files was loaded")

        self.settings_list, self.scan_option_list, plex_list = self.load_config(config=config)
        self.logger.info(msg="config was loaded")
        
        self.path_list = [anime_json, config_file, anime_path, download_path, episode_path]
        self.plex_list = [plex_list[2], plex_list[3]]
        self.file_template = plex_list[0]
        self.folder_template = plex_list[1]



    def check_path(self):
        logs_path = f"{self.data_path}/logs"
        Function.create_path(path=logs_path)

        config_path = f"{self.data_path}/config"
        Function.create_path(path=config_path)

        anime_path = f"{self.data_path}/anime"
        Function.create_path(path=anime_path)

        download_path = f"{self.temp_path}/download"
        Function.create_path(path=download_path)

        episode_path = f"{self.temp_path}/episode"
        Function.create_path(path=episode_path)

        return logs_path, config_path, anime_path, download_path, episode_path
    
    def check_file(self, config_path, anime_path):
        anime_json = f'{config_path}/anime.json'
        if not os.path.exists(anime_json):
            data = [
                {"day": "lundi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "mardi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "mercredi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "jeudi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "vendredi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "samedi","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "dimanche","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "no_day","series": [{"name": "none","season": "none","langage": "none"}]},
                {"day": "download_all","series": [{"name": "none","season": "none","langage": "none"}]}
                ]
            with open(anime_json, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, indent=4, ensure_ascii=False)
            self.logger.warning(msg=f"va ajouter des anime dans le fichier anime.json: {anime_json}")

        
        config_file = f'{config_path}/config.conf'
        config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            config = configparser.ConfigParser(allow_no_value=True)

            config.add_section('settings')
            config.set('settings', '# Niveau de log : info, debug, error')
            config.set('settings', 'level', 'info')
            config.set('settings', '# Nombre de download simultaner')
            config.set('settings', 'threads', '4')
            config.set('settings', '# Intervalle de temps pour chaque scan en secondes')
            config.set('settings', 'timer', '3600')
            
            config.add_section('scan-option')
            config.set('scan-option', '# Options de scan : active ou désactive les scan sur les sites')
            config.set('scan-option', 'anime-sama', 'True')
            config.set('scan-option', '#anime-fr est pas encore dev donc il ne marche pas mais jai prevue de le rajouter')
            config.set('scan-option', 'anime-fr', 'False')
            
            config.add_section('plex')
            config.set('plex', '# pour le moment il a seulment ses variable de disponible. ({name}, {season}, {epsiode})')
            config.set('plex', '# Structure des noms de fichiers.mp4 Plex')
            config.set('plex', '# {name} s{season} {episode} = nom-de-lanime s1 01.mp4')
            config.set('plex', 'mp4_structure', '{name} s{season} {episode}')
            config.set('plex', '# Structure des dossiers Plex')
            config.set('plex', '# /{name}/season {season} = plex_path/nom-de-lanime/season 1/fichier.mp4')
            config.set('plex', 'folders_structure', '/{name}/season {season}')
            config.set('plex', '# Nom du dossier pour les anime en VOSTFR')
            config.set('plex', 'vostfr_folder_name', 'vostfr')
            config.set('plex', '# Nom du dossier pour les anime en VF')
            config.set('plex', 'vf_folder_name', 'vf')
            with open(config_file, 'w') as configfile:
                config.write(configfile)
            self.logger.warning(msg=f"va regarder la configuration: {config_file}")
            time.sleep(1000000)
        config.read(config_file)
        
        
        readme_file = f"{anime_path}/_README.txt"
        if not os.path.exists(readme_file):
            readme_content = """
            Si vous ne souhaitez pas retélécharger tous les animes déjà installés, je vous recommande de ne pas modifier ou supprimer les fichiers présents dans le dossier.
            
            Cependant, si vous rencontrez un problème avec un épisode particulier (corruption, crash en plein milieu de l'épisode), vous pouvez suivre ces étapes pour résoudre le problème :
            
            Étapes à suivre :
            1 - Ouvrez le fichier JSON correspondant à la série et à la saison où l'épisode pose problème.
            2 - Recherchez la ligne correspondant au numéro de l'épisode et supprimez-la.
            3 - Vérifiez que le fichier anime.json dans le dossier config contient toujours les informations sur l'anime, y compris la saison et la langue correspondantes.
            4 - Relancez un scan.
            
            Normalement, cela devrait permettre de réinstaller l'épisode problématique.
            """
            with open(readme_file, "w") as file:
                file.write(readme_content)
        return config, config_file, anime_json

    def load_config(self, config):
        anime_vf = f"{self.plex_path}/{config['plex']['vf_folder_name']}"
        Function.create_path(path=anime_vf)

        anime_vostfr = f"{self.plex_path}/{config['plex']['vostfr_folder_name']}"
        Function.create_path(path=anime_vostfr)

        file_template = config.get('plex', 'mp4_structure')
        folder_template = config.get('plex', 'folders_structure')


        settings_list = [config['settings']['level'], int(config['settings']['threads']), int(config['settings']['timer'])]
        scan_option_list = [bool(config['scan-option']['anime-sama']), bool(config['scan-option']['anime-fr'])]
        plex_list =  [file_template, folder_template, anime_vf, anime_vostfr]

        return settings_list, scan_option_list, plex_list
