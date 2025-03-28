import logging
import os

def setup_logger(name, log_file, path):
    # Vérifier si le chemin est défini
    if path is None:
        raise ValueError("Le chemin du fichier de log n'est pas défini")
        
    # Créer un nouveau logger
    logger = logging.getLogger(name)
    
    # Désactiver la propagation pour éviter les duplications
    logger.propagate = False
    
    # Si le logger a déjà des handlers, on ne fait rien
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)

    # Créer le dossier de logs s'il n'existe pas
    os.makedirs(path, exist_ok=True)

    # Handler pour le fichier
    file_handler = logging.FileHandler(f'{path}/{log_file}')
    file_handler.setLevel(logging.INFO)

    # Handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter pour les logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Ajouter les handlers au logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

_path = None

def sys_logger(path=None):
    global _path
    if path is not None:
        _path = path
    if _path is None:
        raise ValueError("Le chemin du fichier de log n'est pas défini")
    return setup_logger("System", "sys.log", _path)

def queue_logger():
    global _path
    return setup_logger("Queue", "queue.log", _path)

def universal_logger(name="System", log_file="sys.log"):
    global _path
    return setup_logger(name, log_file, _path)

