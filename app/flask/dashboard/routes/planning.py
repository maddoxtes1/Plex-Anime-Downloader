"""
Routes pour la page Planning (planning.html)
"""
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from datetime import datetime
import json
import copy
import configparser
import threading
from flask import copy_current_request_context
from app.flask.dashboard.routes.common import prepare_dashboard_data
from app.sys import FolderConfig, universal_logger
from app.sys.database import anime_details_database, anime_data_database

logger = universal_logger(name="Flask - Planning", log_file="sys.log")

# Noms des fichiers SQLite, utilisés seulement si le chemin n'a pas déjà été
# défini au démarrage de l'app (voir _open_db). Mets ici les MÊMES noms que ceux
# que tu utilises à l'initialisation des bases.
DETAILS_DB_FILE = "anime_details.db"
DATA_DB_FILE = "anime_data.db"

EMPTY_DETAILS = {
    "image": "",
    "description": "",
    "genres": [],
    "seasons": [],
    "seasons_count": 0,
}


def _open_db(db_class, file_name):
    """
    Ouvre une base SQL. Les classes gardent leur chemin en mémoire une fois défini
    (database_path=...), donc on essaie d'abord sans argument. Si Flask tourne dans
    un autre process et que le chemin n'est pas défini, on le fournit nous-mêmes.
    """
    try:
        return db_class()
    except (ValueError, TypeError):
        db_path = FolderConfig.find_path(folder_name="database") / file_name
        return db_class(database_path=str(db_path))


def _get_details_db():
    return _open_db(anime_details_database, DETAILS_DB_FILE)


def _get_data_db():
    return _open_db(anime_data_database, DATA_DB_FILE)


def _enrich_with_details(results, details_db):
    """
    Ajoute real_name / image / description / genres / seasons / seasons_count
    à chaque anime du planning, depuis la base SQL anime_details.
    Si l'anime n'est pas en base, valeurs par défaut.
    """
    for anime in results:
        anime_type = anime.get("type", "")  # "anime-sama" ou "franime"
        lookup_name = None

        if anime_type == "anime-sama":
            lookup_name = anime.get("name")
        elif anime_type == "franime":
            anime_id = anime.get("id_anime")
            if anime_id:
                # Pour franime, id_anime sert de name
                anime["name"] = str(anime_id)
                lookup_name = str(anime_id)

        details = None
        if details_db is not None and lookup_name:
            try:
                details = details_db.get_anime_details(lookup_name)
            except Exception as e:
                logger.error(f"Erreur lecture anime_details pour '{lookup_name}': {e}")

        fallback_name = anime.get("name", anime.get("id_anime", "N/A"))
        if details:
            anime["real_name"] = details.get("title", fallback_name)
            for key, default in EMPTY_DETAILS.items():
                anime[key] = details.get(key, default)
        else:
            anime["real_name"] = fallback_name
            for key, default in EMPTY_DETAILS.items():
                anime[key] = default
    return results


def register_planning_routes(local_bp, helpers, plex_root, config_path):
    """
    Enregistre les routes pour la page Planning.

    Args:
        local_bp: Blueprint Flask
        helpers: Instance de FlaskHelpers
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
    """

    @local_bp.route("/planning")
    def local_dashboard_planning():
        """Page Planning"""
        if not session.get("local_authenticated"):
            flash("Vous devez être connecté avec le mot de passe admin.", "error")
            return redirect(url_for("local.local_login"))

        data = prepare_dashboard_data(helpers, plex_root, config_path)

        # Récupérer planning_scan_data.json depuis config.py:64-66
        database_path = FolderConfig.find_path(folder_name="database")
        planning_data_path = database_path / "planning_scan_data.json"

        planning_results = []
        if planning_data_path.exists():
            try:
                with open(planning_data_path, 'r', encoding='utf-8') as f:
                    planning_data = json.load(f)

                results = planning_data.get("results", [])
                if isinstance(results, list):
                    try:
                        details_db = _get_details_db()
                    except Exception as e:
                        logger.error(f"Impossible d'ouvrir la base anime_details: {e}")
                        details_db = None
                    planning_results = _enrich_with_details(results, details_db)
            except Exception as e:
                logger.error(f"Erreur chargement du planning: {e}")

        data["planning_results"] = planning_results
        return render_template("planning.html", **data)

    @local_bp.route("/local/planning/anime/details", methods=["POST"])
    def local_planning_anime_details():
        """Récupère les détails d'un anime (description, saisons, épisodes installés)"""
        if not session.get("local_authenticated"):
            return jsonify({"error": "Non autorisé"}), 401

        try:
            data = request.get_json(silent=True) or {}
            anime_type = data.get("type", "").strip()  # "anime-sama" ou "franime"
            anime_name = data.get("name", "").strip()  # name pour les deux types
            anime_season = data.get("season", "").strip()
            anime_langage = data.get("langage", "").strip()

            if not anime_name:
                return jsonify({"error": "Le nom de l'anime est requis"}), 400

            # Récupérer l'URL depuis planning_scan_data.json
            database_path = FolderConfig.find_path(folder_name="database")
            planning_data_path = database_path / "planning_scan_data.json"
            anime_url = ""

            if planning_data_path.exists():
                with open(planning_data_path, 'r', encoding='utf-8') as f:
                    planning_data = json.load(f)

                if "results" in planning_data and isinstance(planning_data["results"], list):
                    for item in planning_data["results"]:
                        # Pour franime, comparer avec id_anime si name n'existe pas
                        item_name = item.get("name")
                        if anime_type == "franime" and not item_name:
                            item_name = str(item.get("id_anime", ""))

                        if (item.get("type") == anime_type and
                            item_name == anime_name and
                            item.get("season") == anime_season and
                            item.get("langage") == anime_langage):
                            anime_url = item.get("url", "")
                            break

            # Récupérer les détails depuis la base SQL anime_details
            details_db = _get_details_db()
            details = details_db.get_anime_details(anime_name)
            if not details:
                return jsonify({"error": "Anime non trouvé dans la base de données"}), 404

            # Compter les épisodes depuis la base SQL anime_data
            episodes_installed = 0
            episodes_total = 0

            try:
                plex_path_json = FolderConfig.find_path(file_name="plex_path.json")
                if plex_path_json and plex_path_json.exists():
                    with open(plex_path_json, 'r', encoding='utf-8') as f:
                        plex_data = json.load(f)

                    found_paths = [
                        entry['path'] for entry in plex_data
                        if isinstance(entry, dict) and 'path' in entry and 'language' in entry
                        and anime_langage in entry.get('language', [])
                    ]

                    if found_paths:
                        folder_name = found_paths[0]
                        season_name = f"season {anime_season}"
                        path_list = (folder_name, anime_name, season_name)

                        # get_episode -> [(name, status, urls), ...]
                        episodes = _get_data_db().get_episode(*path_list)
                        episodes_total = len(episodes)
                        episodes_installed = sum(1 for _, status, _ in episodes if status == "downloaded")
            except Exception as e:
                logger.error(f"Erreur comptage des épisodes pour '{anime_name}': {e}")

            result = {
                "title": details.get("title", anime_name),
                "image": details.get("image", ""),
                "description": details.get("description", "Description non disponible"),
                "genres": details.get("genres", []),
                "seasons": details.get("seasons", []),
                "seasons_count": details.get("seasons_count", 0),
                "episodes_installed": episodes_installed,
                "episodes_total": episodes_total,
                "episodes_missing": episodes_total - episodes_installed,
                "anime_url": anime_url,
                "type": anime_type,
                "name": anime_name,
                "season": anime_season,
                "langage": anime_langage
            }

            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @local_bp.route("/local/planning/anime/delete", methods=["POST"])
    def local_planning_anime_delete():
        """Supprime un anime de anime.json et de planning_scan_data.json"""
        if not session.get("local_authenticated"):
            return jsonify({"error": "Non autorisé"}), 401

        try:
            data = request.get_json(silent=True) or {}
            anime_type = data.get("type", "").strip()  # "anime-sama" ou "franime"
            anime_name = data.get("name", "").strip()  # name pour les deux types
            anime_season = data.get("season", "").strip()
            anime_langage = data.get("langage", "").strip()

            if not anime_name:
                return jsonify({"error": "Le nom de l'anime est requis"}), 400

            # Supprimer de planning_scan_data.json
            planning_scan_data = FolderConfig.find_path(file_name="planning_scan_data.json")
            deleted_from_planning = False
            item_found = None

            if planning_scan_data and planning_scan_data.exists():
                with open(planning_scan_data, 'r', encoding='utf-8') as file:
                    planning_data = json.load(file)

                # Chercher et mettre à jour l'item dans results
                if "results" in planning_data:
                    for item in planning_data["results"]:
                        # Pour franime, comparer avec id_anime si name n'existe pas
                        item_name = item.get("name")
                        if anime_type == "franime" and not item_name:
                            item_name = str(item.get("id_anime", ""))

                        if (item.get("type") == anime_type and
                            item_name == anime_name and
                            item.get("season") == anime_season and
                            item.get("langage") == anime_langage and
                            item.get("found") == False):
                            item["status"] = "2"
                            item_found = item
                            break

                # Si auto_delete activé, retirer l'item et supprimer de anime.json
                config_path = FolderConfig.find_path(file_name="config.conf")
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_path, encoding='utf-8')

                if anime_type == "anime-sama":
                    auto_delete = config.get("scan-option", "anime-sama-auto-delete", fallback="false")
                else:
                    auto_delete = config.get("scan-option", "franime-auto-delete", fallback="false")

                if auto_delete.lower() == "true" and item_found:
                    planning_data["results"].remove(item_found)
                    planning_data["total"] = len(planning_data["results"])
                    deleted_from_planning = True

                    # Retirer de anime.json
                    anime_json = FolderConfig.find_path(file_name="anime.json")
                    if anime_json and anime_json.exists():
                        with open(anime_json, 'r', encoding='utf-8') as file:
                            anime_data = json.load(file)

                        for entry in anime_data:
                            if "auto_download" in entry:
                                for day in entry["auto_download"]:
                                    # Pour franime, comparer avec id_anime si name n'existe pas
                                    entry["auto_download"][day] = [
                                        a for a in entry["auto_download"][day]
                                        if not (a.get("name") == anime_name or
                                               (anime_type == "franime" and not a.get("name") and str(a.get("id_anime")) == anime_name))
                                    ]
                            if "single_download" in entry:
                                # Pour franime, comparer avec id_anime si name n'existe pas
                                entry["single_download"] = [
                                    a for a in entry["single_download"]
                                    if not (a.get("name") == anime_name or
                                           (anime_type == "franime" and not a.get("name") and str(a.get("id_anime")) == anime_name))
                                ]

                        with open(anime_json, 'w', encoding='utf-8') as file:
                            json.dump(anime_data, file, indent=4, ensure_ascii=False)

                # Sauvegarder planning_scan_data.json
                with open(planning_scan_data, 'w', encoding='utf-8') as file:
                    json.dump(planning_data, file, indent=4, ensure_ascii=False)

            return jsonify({
                "success": True,
                "deleted_from_planning": deleted_from_planning,
                "message": "Anime supprimé avec succès"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @local_bp.route("/local/planning/status", methods=["GET"])
    def local_planning_status():
        """Récupère le statut du scan du planning depuis planning_scan_data.json"""
        if not session.get("local_authenticated"):
            return jsonify({"error": "Non autorisé"}), 401

        try:
            database_path = FolderConfig.find_path(folder_name="database")
            planning_data_path = database_path / "planning_scan_data.json"

            if planning_data_path.exists():
                with open(planning_data_path, 'r', encoding='utf-8') as f:
                    planning_data = json.load(f)

                # Récupérer le statut depuis planning_scan_data.json
                if "status" in planning_data:
                    return jsonify(planning_data["status"])
                else:
                    return jsonify({"status": "idle", "started_at": None, "completed_at": None, "error": None})
            else:
                return jsonify({"status": "idle", "started_at": None, "completed_at": None, "error": None})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @local_bp.route("/local/planning/data", methods=["GET"])
    def local_planning_data():
        """Récupère les données du dernier scan du planning enrichies avec anime_details_database"""
        if not session.get("local_authenticated"):
            return jsonify({"error": "Non autorisé"}), 401

        try:
            database_path = FolderConfig.find_path(folder_name="database")
            data_path = database_path / "planning_scan_data.json"

            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Enrichir les résultats avec la base SQL anime_details
                if isinstance(data.get("results"), list):
                    try:
                        details_db = _get_details_db()
                    except Exception as e:
                        logger.error(f"Impossible d'ouvrir la base anime_details: {e}")
                        details_db = None
                    _enrich_with_details(data["results"], details_db)

                return jsonify(data)
            else:
                return jsonify({"results": [], "scan_date": None, "total": 0, "message": "Aucune donnée disponible"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @local_bp.route("/local/planning/scan", methods=["POST"])
    def local_planning_scan():
        """Lance un scan manuel du planning"""
        if not session.get("local_authenticated"):
            return jsonify({"error": "Non autorisé"}), 401

        try:
            from app.streaming.manager import function

            # Vérifier si un scan est déjà en cours
            database_path = FolderConfig.find_path(folder_name="database")
            planning_data_path = database_path / "planning_scan_data.json"

            if planning_data_path.exists():
                with open(planning_data_path, 'r', encoding='utf-8') as f:
                    planning_data = json.load(f)

                if "status" in planning_data and planning_data["status"].get("status") == "running":
                    return jsonify({"status": "running", "message": "Un scan est déjà en cours"})

            # Sauvegarder le statut "running" immédiatement dans le fichier avant de lancer le thread
            if planning_data_path.exists():
                with open(planning_data_path, 'r', encoding='utf-8') as f:
                    planning_data = json.load(f)
            else:
                planning_data = {"results": [], "total": 0}

            # Mettre à jour le statut à "running" immédiatement
            from datetime import datetime
            planning_data["status"] = {
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "error": None
            }
            with open(planning_data_path, 'w', encoding='utf-8') as f:
                json.dump(planning_data, f, indent=4, ensure_ascii=False)

            # Lancer le scan dans un thread
            @copy_current_request_context
            def run_scan():
                try:
                    # Créer une instance de planning_scan et lancer le scan
                    func = function()
                    planning_scan_instance = func.planning_scan()
                    planning_scan_instance.run()
                except Exception as e:
                    # En cas d'erreur, mettre à jour le statut dans planning_scan_data.json
                    if planning_data_path.exists():
                        with open(planning_data_path, 'r', encoding='utf-8') as f:
                            planning_data = json.load(f)
                        planning_data["status"] = {
                            "status": "error",
                            "error": str(e),
                            "started_at": planning_data.get("status", {}).get("started_at"),
                            "completed_at": datetime.now().isoformat()
                        }
                        with open(planning_data_path, 'w', encoding='utf-8') as f:
                            json.dump(planning_data, f, indent=4, ensure_ascii=False)

            # Démarrer le thread
            scan_thread = threading.Thread(target=run_scan, daemon=True)
            scan_thread.start()

            return jsonify({"status": "started", "message": "Scan du planning démarré"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
