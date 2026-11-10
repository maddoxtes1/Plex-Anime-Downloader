import os
import json
import sqlite3
import threading
from contextlib import contextmanager

from .system import universal_logger

_DATABASE_LOCKS = {}
_DATABASE_LOCKS_GUARD = threading.Lock()


def get_database_lock(path):
    path = os.path.abspath(path)

    with _DATABASE_LOCKS_GUARD:
        if path not in _DATABASE_LOCKS:
            _DATABASE_LOCKS[path] = threading.RLock()

        return _DATABASE_LOCKS[path]


def _to_json(value):
    """Convertit une valeur Python en texte JSON (pour les listes stockées dans une colonne)."""
    return json.dumps(value, ensure_ascii=False)


def _from_json(text, default=None):
    """Convertit un texte JSON en valeur Python."""
    if text is None:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


class BaseDatabase:
    """
    Classe de base pour toutes les bases de données SQLite.
    Gère la connexion, les verrous et la création des tables.
    """
    # À définir dans les sous-classes
    _SCHEMA = ""        # Script SQL de création des tables

    def __init__(self, database_path, logger_name, allow_file_not_found=False):
        """
        Initialise la base de données.

        Args:
            database_path (str): Chemin vers le fichier SQLite (.db) de la base de données
            logger_name (str): Nom du logger
            allow_file_not_found (bool): Gardé pour compatibilité (SQLite crée le fichier tout seul)
        """
        if database_path is None:
            raise ValueError(f"Le chemin du fichier de base de données n'est pas défini pour {logger_name}")

        if str(database_path).lower().endswith(".json"):
            raise ValueError(f"'{database_path}' est un fichier JSON pour {logger_name}: utilise un fichier .db")

        self.database_path = database_path
        self._lock = get_database_lock(self.database_path)
        self.logger = universal_logger(logger_name, "sys.log")
        self.allow_file_not_found = allow_file_not_found

        folder = os.path.dirname(os.path.abspath(self.database_path))
        os.makedirs(folder, exist_ok=True)

        with self._lock:
            self._init_schema()

    # ------------------------------------------------------------------
    # Connexion / transactions
    # ------------------------------------------------------------------
    def _connect(self):
        conn = sqlite3.connect(self.database_path, timeout=30)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _db(self):
        """
        Ouvre une connexion dans une transaction.
        Commit automatique à la fin, rollback si une erreur survient.
        """
        with self._lock:
            conn = self._connect()
            try:
                with conn:
                    yield conn
            except Exception as e:
                self.logger.error(f"Erreur SQL sur '{self.database_path}': {e}")
                raise
            finally:
                conn.close()

    def _init_schema(self):
        conn = self._connect()
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(self._SCHEMA)
            conn.commit()
        finally:
            conn.close()


class anime_data_database(BaseDatabase):
    """
    Base de données pour stocker les données des animes (séries, saisons, épisodes).
    Gère la structure hiérarchique : path -> series -> season -> episodes

    Tables SQL : paths -> series -> seasons -> episodes
    (la suppression d'un parent supprime automatiquement ses enfants)
    """
    anime_data_path = None

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS paths (
        name TEXT PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS series (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        path_name TEXT NOT NULL REFERENCES paths(name) ON DELETE CASCADE,
        name      TEXT NOT NULL,
        UNIQUE (path_name, name)
    );

    CREATE TABLE IF NOT EXISTS seasons (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
        name      TEXT NOT NULL,
        UNIQUE (series_id, name)
    );

    CREATE TABLE IF NOT EXISTS episodes (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
        name      TEXT NOT NULL,
        status    TEXT NOT NULL DEFAULT 'not_downloaded',
        url       TEXT NOT NULL DEFAULT '[]',
        UNIQUE (season_id, name)
    );

    CREATE INDEX IF NOT EXISTS idx_episodes_season_status ON episodes (season_id, status);
    """

    def __init__(self, database_path=None):
        if database_path is not None:
            anime_data_database.anime_data_path = database_path
        if anime_data_database.anime_data_path is None:
            raise ValueError("Le chemin du fichier de base de données anime-data n'est pas défini")
        super().__init__(anime_data_database.anime_data_path, "AnimeDataDatabase", allow_file_not_found=False)

    # ------------------------------------------------------------------
    # Vérifications (renvoient l'id trouvé, ou None / False)
    # ------------------------------------------------------------------
    def _verify_path(self, conn, path_name):
        """
        Vérifie si un chemin (path) existe dans la base de données.

        Returns:
            bool: True si le chemin existe, False sinon
        """
        row = conn.execute("SELECT 1 FROM paths WHERE name = ?", (path_name,)).fetchone()
        if row is None:
            self.logger.error(f"Le chemin '{path_name}' n'existe pas dans la base de données")
            return False
        return True

    def _verify_series(self, conn, path_name, series_name):
        """
        Vérifie qu'une série existe dans un chemin donné.

        Returns:
            int | None: L'id de la série, ou None si elle n'existe pas
        """
        if not self._verify_path(conn, path_name):
            return None
        row = conn.execute(
            "SELECT id FROM series WHERE path_name = ? AND name = ?", (path_name, series_name)
        ).fetchone()
        if row is None:
            self.logger.error(f"La série '{series_name}' n'existe pas dans le chemin '{path_name}'")
            return None
        return row[0]

    def _verify_season(self, conn, path_name, series_name, season_name):
        """
        Vérifie qu'une saison existe dans une série donnée.

        Returns:
            int | None: L'id de la saison, ou None si elle n'existe pas
        """
        series_id = self._verify_series(conn, path_name, series_name)
        if series_id is None:
            return None
        row = conn.execute(
            "SELECT id FROM seasons WHERE series_id = ? AND name = ?", (series_id, season_name)
        ).fetchone()
        if row is None:
            self.logger.error(f"La saison '{season_name}' n'existe pas dans la série '{series_name}' dans le chemin '{path_name}'")
            return None
        return row[0]

    # ------------------------------------------------------------------
    # Chemins
    # ------------------------------------------------------------------
    def get_existing_path(self):
        """
        Récupère la liste de tous les chemins (paths) existants dans la base de données.

        Returns:
            list: Liste des noms de chemins
        """
        with self._db() as conn:
            rows = conn.execute("SELECT name FROM paths ORDER BY rowid").fetchall()
        return [row[0] for row in rows]

    def add_path(self, path_name):
        """
        Ajoute un nouveau chemin (path) dans la base de données.
        Si le chemin existe déjà, ne fait rien.
        """
        with self._db() as conn:
            cursor = conn.execute("INSERT OR IGNORE INTO paths (name) VALUES (?)", (path_name,))
            if cursor.rowcount:
                self.logger.debug(f"Chemin '{path_name}' ajouté avec succès")

    def delete_path(self, path_name):
        """
        Supprime un chemin (path) et tout son contenu (séries, saisons, épisodes).
        """
        with self._db() as conn:
            cursor = conn.execute("DELETE FROM paths WHERE name = ?", (path_name,))
            if cursor.rowcount:
                self.logger.debug(f"Chemin '{path_name}' supprimé avec succès")

    # ------------------------------------------------------------------
    # Séries / saisons
    # ------------------------------------------------------------------
    def add_series(self, path_name, series_name):
        """
        Ajoute une nouvelle série dans un chemin donné.
        Vérifie d'abord que le chemin existe. Si la série existe déjà, ne fait rien.
        """
        with self._db() as conn:
            if self._verify_path(conn, path_name):
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO series (path_name, name) VALUES (?, ?)", (path_name, series_name)
                )
                if cursor.rowcount:
                    self.logger.debug(f"Série '{series_name}' ajoutée avec succès dans le chemin '{path_name}'")

    def add_season(self, path_name, series_name, season_name):
        """
        Ajoute une nouvelle saison dans une série donnée.
        Vérifie d'abord que le chemin et la série existent. Si la saison existe déjà, ne fait rien.
        """
        with self._db() as conn:
            series_id = self._verify_series(conn, path_name, series_name)
            if series_id is not None:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO seasons (series_id, name) VALUES (?, ?)", (series_id, season_name)
                )
                if cursor.rowcount:
                    self.logger.debug(f"Saison '{season_name}' ajoutée avec succès dans la série '{series_name}' dans le chemin '{path_name}'")

    # ------------------------------------------------------------------
    # Épisodes
    # ------------------------------------------------------------------
    def add_episode(self, path_name, series_name, season_name, episode_list):
        """
        Ajoute (ou modifie s'il existe déjà) un épisode dans une saison donnée.

        Args:
            episode_list (tuple): (episode_name, episode_status, episode_url)
                - episode_name (str): Le nom de l'épisode
                - episode_status (str): Le statut (ex: "not_downloaded", "downloaded")
                - episode_url (list): Liste des URLs de l'épisode pour chaque domaine
        """
        with self._db() as conn:
            season_id = self._verify_season(conn, path_name, series_name, season_name)
            if season_id is not None:
                episode_name, episode_status, episode_url = episode_list
                conn.execute(
                    """
                    INSERT INTO episodes (season_id, name, status, url)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (season_id, name)
                    DO UPDATE SET url = excluded.url
                    """,
                    (season_id, episode_name, episode_status, _to_json(episode_url))
                )
                self.logger.debug(f"Episode '{episode_name}' ajouté/modifier avec succès dans la saison '{season_name}' dans la série '{series_name}' dans le chemin '{path_name}'")

    def get_episode(self, path_name, series_name, season_name):
        """
        Récupère tous les épisodes d'une saison donnée.

        Returns:
            list: Liste de tuples (episode_name, episode_status, episode_url) pour chaque épisode
        """
        with self._db() as conn:
            season_id = self._verify_season(conn, path_name, series_name, season_name)
            if season_id is None:
                return []
            rows = conn.execute(
                "SELECT name, status, url FROM episodes WHERE season_id = ? ORDER BY id", (season_id,)
            ).fetchall()
        return [(name, status, _from_json(url, [])) for name, status, url in rows]

    def update_episode_status(self, path_name, series_name, season_name, episode_name, episode_status):
        with self._db() as conn:
            season_id = self._verify_season(conn, path_name, series_name, season_name)
            if season_id is None:
                self.logger.debug(f"Saison introuvable: {path_name}/{series_name}/{season_name}")
                return False

            cursor = conn.execute(
                "UPDATE episodes SET status = ? WHERE season_id = ? AND name = ?",
                (str(episode_status), season_id, episode_name)
            )
            if cursor.rowcount == 0:
                noms = [r[0] for r in conn.execute(
                    "SELECT name FROM episodes WHERE season_id = ?", (season_id,)
                ).fetchall()]
                self.logger.debug(f"Episode {episode_name!r} introuvable. Noms en base: {noms}")
                return False

            conn.commit()  # <-- important si _db() ne commit pas
            self.logger.debug(f"Status update: {episode_name!r} -> {episode_status!r}")
            return True

    def get_unistalled_episode(self, path_list):
        path_name, series_name, season_name = path_list
        with self._db() as conn:
            season_id = self._verify_season(conn, path_name, series_name, season_name)
            if season_id is None:
                self.logger.debug(f"Saison introuvable: {path_list}")
                return []

            # --- DEBUG : voir tous les statuts de la saison ---
            all_rows = conn.execute(
                "SELECT id, name, status FROM episodes WHERE season_id = ? ORDER BY id",
                (season_id,)
            ).fetchall()
            for ep_id, name, status in all_rows:
                self.logger.debug(f"[season {season_id}] id#{ep_id} '{name}' -> status={status!r}")

            counts = conn.execute(
                "SELECT status, COUNT(*) FROM episodes WHERE season_id = ? GROUP BY status",
                (season_id,)
            ).fetchall()
            self.logger.debug(f"[season {season_id}] répartition des statuts: {dict(counts)}")
            # --- FIN DEBUG ---

            rows = conn.execute(
                "SELECT name, url FROM episodes WHERE season_id = ? AND status = 'not_downloaded' ORDER BY id",
                (season_id,)
            ).fetchall()

        self.logger.debug(f"{len(rows)} épisode(s) not_downloaded trouvé(s): {[name for name, _ in rows]}")
        return [(name, _from_json(url, [])) for name, url in rows]


class anime_details_database(BaseDatabase):
    """
    Base de données pour stocker les détails des animes (titre, image, description, genres, saisons).
    Permet de mettre en cache les informations extraites depuis anime-sama pour éviter les requêtes HTTP répétées.

    Structure des données retournées (identique à avant):
        {
            "title": str,
            "image": str,
            "description": str,
            "genres": list[str],
            "seasons": list[str],
            "seasons_count": int
        }
    Les clés supplémentaires éventuelles sont conservées dans la colonne 'extra'.
    """
    _anime_details_path = None

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS anime_details (
        name          TEXT PRIMARY KEY,
        title         TEXT,
        image         TEXT,
        description   TEXT,
        genres        TEXT,
        seasons       TEXT,
        seasons_count INTEGER,
        extra         TEXT NOT NULL DEFAULT '{}'
    );
    """

    _TEXT_FIELDS = ("title", "image", "description")
    _JSON_FIELDS = ("genres", "seasons")
    _KNOWN_FIELDS = _TEXT_FIELDS + _JSON_FIELDS + ("seasons_count",)

    def __init__(self, database_path=None):
        if database_path is not None:
            anime_details_database._anime_details_path = database_path
        if anime_details_database._anime_details_path is None:
            raise ValueError("Le chemin du fichier de base de données anime-details n'est pas défini")
        super().__init__(anime_details_database._anime_details_path, "AnimeDetailsDatabase", allow_file_not_found=True)

    # ------------------------------------------------------------------
    # Conversion dict <-> ligne SQL
    # ------------------------------------------------------------------
    def _upsert(self, conn, anime_name, details):
        extra = {k: v for k, v in details.items() if k not in self._KNOWN_FIELDS}
        conn.execute(
            """
            INSERT INTO anime_details (name, title, image, description, genres, seasons, seasons_count, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                title = excluded.title,
                image = excluded.image,
                description = excluded.description,
                genres = excluded.genres,
                seasons = excluded.seasons,
                seasons_count = excluded.seasons_count,
                extra = excluded.extra
            """,
            (
                anime_name,
                details.get("title"),
                details.get("image"),
                details.get("description"),
                _to_json(details["genres"]) if "genres" in details else None,
                _to_json(details["seasons"]) if "seasons" in details else None,
                details.get("seasons_count"),
                _to_json(extra),
            )
        )

    def _fetch(self, conn, anime_name):
        row = conn.execute(
            "SELECT title, image, description, genres, seasons, seasons_count, extra FROM anime_details WHERE name = ?",
            (anime_name,)
        ).fetchone()
        if row is None:
            return None

        title, image, description, genres, seasons, seasons_count, extra = row
        details = {}
        if title is not None:
            details["title"] = title
        if image is not None:
            details["image"] = image
        if description is not None:
            details["description"] = description
        if genres is not None:
            details["genres"] = _from_json(genres, [])
        if seasons is not None:
            details["seasons"] = _from_json(seasons, [])
        if seasons_count is not None:
            details["seasons_count"] = seasons_count
        details.update(_from_json(extra, {}))
        return details

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def get_anime_details(self, anime_name):
        """
        Récupère les détails d'un anime depuis la base de données.

        Args:
            anime_name (str): Nom de l'anime (ex: maou-no-musume-wa-yasashi-sugiru)

        Returns:
            dict: Dictionnaire avec 'title', 'image', 'description', 'genres', 'seasons', 'seasons_count',
                  ou None si l'anime n'est pas dans la base de données
        """
        with self._db() as conn:
            details = self._fetch(conn, anime_name)
        if details is not None:
            self.logger.debug(f"Détails de '{anime_name}' trouvés dans le cache")
        return details

    def save_anime_details(self, anime_name, details):
        """
        Sauvegarde (ou remplace) les détails d'un anime dans la base de données.

        Args:
            anime_name (str): Nom de l'anime
            details (dict): Dictionnaire contenant 'title', 'image', 'description', 'genres', 'seasons', 'seasons_count'
        """
        with self._db() as conn:
            self._upsert(conn, anime_name, details)
        self.logger.debug(f"Détails de '{anime_name}' sauvegardés dans le cache")

    def update_anime_details(self, anime_name, details):
        """
        Met à jour les détails d'un anime existant dans la base de données.
        S'il n'existe pas encore, il est créé.

        Args:
            anime_name (str): Nom de l'anime
            details (dict): Dictionnaire contenant les nouvelles informations
        """
        with self._db() as conn:
            existing = self._fetch(conn, anime_name)
            if existing is None:
                self.logger.warning(f"Tentative de mise à jour de '{anime_name}' qui n'existe pas. Utilisation de save_anime_details.")
                self._upsert(conn, anime_name, details)
            else:
                existing.update(details)
                self._upsert(conn, anime_name, existing)
                self.logger.debug(f"Détails de '{anime_name}' mis à jour dans le cache")

    def delete_anime_details(self, anime_name):
        """
        Supprime les détails d'un anime de la base de données.

        Args:
            anime_name (str): Nom de l'anime à supprimer
        """
        with self._db() as conn:
            cursor = conn.execute("DELETE FROM anime_details WHERE name = ?", (anime_name,))
        if cursor.rowcount:
            self.logger.debug(f"Détails de '{anime_name}' supprimés du cache")
        else:
            self.logger.warning(f"Tentative de suppression de '{anime_name}' qui n'existe pas dans le cache")

    def get_all_anime_names(self):
        """
        Récupère la liste de tous les noms d'anime dans la base de données.

        Returns:
            list: Liste des noms d'anime
        """
        with self._db() as conn:
            rows = conn.execute("SELECT name FROM anime_details ORDER BY rowid").fetchall()
        return [row[0] for row in rows]

    def clear_cache(self):
        """Vide complètement le cache des détails d'anime"""
        with self._db() as conn:
            conn.execute("DELETE FROM anime_details")
        self.logger.info("Cache des détails d'anime vidé")
