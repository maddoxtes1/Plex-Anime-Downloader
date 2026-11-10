"""
Accès centralisé aux bases SQL (app/sys/db_access.py).

Les classes anime_details_database / anime_data_database gardent leur chemin en
mémoire une fois défini. Ici, on essaie d'abord sans argument (chemin déjà défini
dans ce process), sinon on fournit le chemin nous-mêmes. Comme ça, le scraper,
le manager et Flask ouvrent TOUJOURS la même base.
"""
from . import FolderConfig
from .database import anime_details_database, anime_data_database

DETAILS_DB_FILE = "anime_details.db"
DATA_DB_FILE = "anime_data.db"


def _db_file(file_name):
    return str(FolderConfig.find_path(folder_name="database") / file_name)


def get_details_db():
    try:
        return anime_details_database()
    except ValueError:
        return anime_details_database(database_path=_db_file(DETAILS_DB_FILE))


def get_data_db():
    try:
        return anime_data_database()
    except (ValueError, TypeError):
        return anime_data_database(database_path=_db_file(DATA_DB_FILE))
