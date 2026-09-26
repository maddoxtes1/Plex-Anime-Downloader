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
from app.sys import FolderConfig


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

                # Charger anime_details_database (database.py:308)
                from app.sys.database import anime_details_database
                anime_details_path = FolderConfig.find_path(file_name="anime_details.json")

                if anime_details_path and anime_details_path.exists():
                    details_db = anime_details_database(database_path=str(anime_details_path))

                    # Parcourir les résultats du scan
                    if "results" in planning_data and isinstance(planning_data["results"], list):
                        for anime in planning_data["results"]:
                            anime_type = anime.get("type", "")  # "anime-sama" ou "franime"
                            anime_details = None

                            # Chercher dans anime_details_database selon le type
                            if anime_type == "anime-sama":
                                anime_name = anime.get("name")
                                if anime_name:
                                    anime_details = details_db.get_anime_details(anime_name)
                            elif anime_type == "franime":
                                anime_id = anime.get("id_anime")
                                if anime_id:
                                    # Pour franime, utiliser id_anime comme name pour la recherche
                                    anime["name"] = str(anime_id)  # Ajouter name = id_anime pour franime
                                    anime_details = details_db.get_anime_details(str(anime_id))

                            # Enrichir les données de l'anime avec les informations de la database
                            if anime_details:
                                anime["real_name"] = anime_details.get("title", anime.get("name", anime.get("id_anime", "N/A")))
                                anime["image"] = anime_details.get("image", "")
                                anime["description"] = anime_details.get("description", "")
                                anime["genres"] = anime_details.get("genres", [])
                                anime["seasons"] = anime_details.get("seasons", [])
                                anime["seasons_count"] = anime_details.get("seasons_count", 0)
                            else:
                                # Si l'anime n'est pas dans la database, utiliser les valeurs par défaut
                                anime["real_name"] = anime.get("name", anime.get("id_anime", "N/A"))
                                anime["image"] = ""
                                anime["description"] = ""
                                anime["genres"] = []
                                anime["seasons"] = []
                                anime["seasons_count"] = 0

                            planning_results.append(anime)
                else:
                    # Si anime_details.json n'existe pas, utiliser les données brutes
                    if "results" in planning_data and isinstance(planning_data["results"], list):
                        for anime in planning_data["results"]:
                            anime["real_name"] = anime.get("name", anime.get("id_anime", "N/A"))
                            anime["image"] = ""
                            planning_results.append(anime)
            except Exception as e:
                # En cas d'erreur, on continue avec une liste vide
                pass

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

            # Récupérer les détails depuis anime_details_database
            from app.sys.database import anime_details_database, anime_data_database
            from app.sys import EnvConfig
            import os

            anime_details_path = FolderConfig.find_path(file_name="anime_details.json")
            if not anime_details_path:
                return jsonify({"error": "Base de données anime_details.json non trouvée"}), 404

            details_db = anime_details_database(database_path=str(anime_details_path))

            # Récupérer les détails depuis la database (utilise le name pour les deux types)
            details = details_db.get_anime_details(anime_name)
            if not details:
                return jsonify({"error": "Anime non trouvé dans la base de données"}), 404

            # Compter les épisodes installés dans la database
            episodes_installed = 0
            episodes_total = 0

            try:
                # Récupérer le path pour cette langue
                plex_path_json = FolderConfig.find_path(file_name="plex_path.json")
                if plex_path_json and plex_path_json.exists():
                    with open(plex_path_json, 'r', encoding='utf-8') as f:
                        plex_data = json.load(f)

                    path_entries = [item for item in plex_data if isinstance(item, dict) and 'path' in item and 'language' in item]
                    found_paths = []
                    for entry in path_entries:
                        if anime_langage in entry.get('language', []):
                            found_paths.append(entry['path'])

                    if found_paths:
                        folder_name = found_paths[0]
                        plex_path = EnvConfig.get_env("plex_path")
                        path_name = os.path.join(plex_path, folder_name)

                        # Construire le path_list (utilise le name pour les deux types)
                        season_name = f"season {anime_season}"
                        path_list = (folder_name, anime_name, season_name)

                        # Interroger la database
                        anime_data_path = FolderConfig.find_path(file_name="anime_data.json")
                        if anime_data_path:
                            db = anime_data_database(database_path=str(anime_data_path))
                            all_episodes = db.get_all_episodes(path_list)
                            installed_episodes = db.get_installed_episodes(path_list)
                        else:
                            all_episodes = []
                            installed_episodes = []

                        episodes_total = len(all_episodes) if all_episodes else 0
                        episodes_installed = len(installed_episodes) if installed_episodes else 0
            except Exception as e:
                # Si erreur, on continue sans les infos d'épisodes
                pass

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

                # Enrichir les résultats avec anime_details_database
                from app.sys.database import anime_details_database
                anime_details_path = FolderConfig.find_path(file_name="anime_details.json")

                if anime_details_path and anime_details_path.exists() and "results" in data:
                    details_db = anime_details_database(database_path=str(anime_details_path))

                    for anime in data["results"]:
                        anime_type = anime.get("type", "")
                        anime_details = None

                        # Chercher dans anime_details_database selon le type
                        if anime_type == "anime-sama":
                            anime_name = anime.get("name")
                            if anime_name:
                                anime_details = details_db.get_anime_details(anime_name)
                        elif anime_type == "franime":
                            anime_id = anime.get("id_anime")
                            if anime_id:
                                # Pour franime, utiliser id_anime comme name pour la recherche
                                anime["name"] = str(anime_id)  # Ajouter name = id_anime pour franime
                                anime_details = details_db.get_anime_details(str(anime_id))

                        # Enrichir les données
                        if anime_details:
                            anime["real_name"] = anime_details.get("title", anime.get("name", anime.get("id_anime", "N/A")))
                            anime["image"] = anime_details.get("image", "")
                            anime["description"] = anime_details.get("description", "")
                            anime["genres"] = anime_details.get("genres", [])
                            anime["seasons"] = anime_details.get("seasons", [])
                            anime["seasons_count"] = anime_details.get("seasons_count", 0)
                        else:
                            anime["real_name"] = anime.get("name", anime.get("id_anime", "N/A"))
                            anime["image"] = ""
                            anime["description"] = ""
                            anime["genres"] = []
                            anime["seasons"] = []
                            anime["seasons_count"] = 0

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
