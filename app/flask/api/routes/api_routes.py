"""
Routes pour l'API JSON (extension navigateur)
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from app.flask.dashboard.themes import get_theme_colors, get_available_themes
import os
import re

def create_api_blueprint(helpers, queue_manager=None):
    """
    Crée le blueprint pour les routes API.
    
    Args:
        helpers: Instance de FlaskHelpers
        queue_manager: Instance de queues pour ajouter des téléchargements
    """
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    @api_bp.route("/ping", methods=["GET"])
    def api_ping():
        """Permet à l'extension de tester la connexion au serveur."""
        return jsonify({"ok": True, "message": "pong"}), 200

    @api_bp.route("/login", methods=["POST"])
    def api_login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return (
                jsonify(
                    {"ok": False, "error": "username et password obligatoires"},
                ),
                400,
            )

        user = helpers.get_user_by_username(username)
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"ok": False, "error": "identifiants invalides"}), 401

        return jsonify({"ok": True, "user": username}), 200

    @api_bp.route("/dashboard", methods=["GET"])
    def api_dashboard():
        """Retourne un 'dashboard' JSON simple pour l'extension."""
        username = request.args.get("user") or "inconnu"
        return jsonify(
            {
                "ok": True,
                "user": username,
                "data": {
                    "title": "Dashboard API",
                    "message": f"Bienvenue sur ton dashboard, {username} !",
                },
            }
        ), 200

    @api_bp.route("/add-download", methods=["POST"])
    def api_add_download():
        """Ajoute un anime dans anime.json."""
        data = request.get_json(silent=True) or {}
        anime_url = data.get("anime_url", "").strip()
        
        # Gérer le cas où day peut être None ou une chaîne vide
        day_raw = data.get("day")
        if day_raw is None or day_raw == "":
            day = None
        else:
            day = str(day_raw).strip().lower()  # Jour de la semaine (lundi, mardi, etc.)

        if not anime_url:
            return jsonify({"ok": False, "error": "anime_url est obligatoire"}), 400

        try:
            # Déconstruire l'URL
            # Format: /catalogue/egao-no-taenai-shokuba-desu/saison1/vostfr
            if "/catalogue/" not in anime_url:
                return jsonify({"ok": False, "error": "URL d'anime invalide (doit contenir /catalogue/)"}), 400

            # Extraire les informations depuis l'URL
            # Normaliser l'URL : enlever le slash final si présent
            normalized_url = anime_url.rstrip("/")
            if "/catalogue/" not in normalized_url:
                return jsonify({"ok": False, "error": "URL d'anime invalide (doit contenir /catalogue/)"}), 400
            
            parts = normalized_url.split("/catalogue/")[1].split("/")
            
            if len(parts) < 3:
                return jsonify({"ok": False, "error": "URL d'anime invalide (format attendu: /catalogue/{name}/saison{season}/{langage})"}), 400

            name = parts[0]  # egao-no-taenai-shokuba-desu
            
            # Extraire la saison (saison1 -> 1, saison1-2 -> 1-2)
            season_str = parts[1] if len(parts) > 1 else "saison1"
            # Enlever "saison" ou "Saison" du début, mais conserver le reste (y compris les tirets)
            # Utiliser une regex pour extraire proprement - enlever seulement au début (insensible à la casse)
            season_match = re.sub(r'^[Ss]aison', '', season_str, flags=re.IGNORECASE)
            
            # Debug: vérifier ce qui est extrait
            # print(f"DEBUG: season_str={season_str}, season_match={season_match}")
            
            # Vérifier si la saison contient des lettres après le numéro (ex: saison1hs)
            # Accepter les saisons avec tirets (ex: saison1-2) mais rejeter celles avec lettres
            # Pattern: commence par des chiffres, suivi directement de lettres (sans tiret) → non supporté
            if season_match and re.search(r'^\d+[a-zA-Z]+', season_match):
                # Pattern: chiffres suivis directement de lettres (sans tiret) → non supporté
                return jsonify({
                    "ok": False,
                    "error": "Ce type de saison n'est pas supporté (ex: saison1hs). Veuillez utiliser la version standard (ex: saison1) ou avec tirets (ex: saison1-2)."
                }), 400
            
            # Accepter les saisons simples (1) ou avec tirets (1-2, 3-5, etc.)
            # Le format sera conservé tel quel (ex: "1-2" au lieu de "1")
            # S'assurer que season_match n'est pas vide
            if not season_match or season_match.strip() == "":
                season = "1"
            else:
                season = season_match.strip()  # Conserver le format exact (1-2, 3-5, etc.)
            
            # Extraire le langage
            langage = parts[2] if len(parts) > 2 else "vostfr"
            
            streaming = "anime-sama"
            file_name = "none"

            # Valider le jour si fourni
            valid_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            if day and day not in valid_days:
                day = None  # Si jour invalide, mettre dans single_download

            # Vérifier d'abord si l'anime existe déjà
            # Debug: vérifier les paramètres de recherche
            # print(f"DEBUG: Recherche anime - name={name}, season={season}, langage={langage}")
            exists_result = helpers.check_anime_in_json(name, season, langage)
            # print(f"DEBUG: exists_result={exists_result}")
            
            if exists_result["exists"]:
                # L'anime existe déjà, retourner un statut clair
                return jsonify({
                    "ok": True,
                    "already_exists": True,
                    "message": "Cet anime est déjà dans la liste",
                    "anime": {
                        "name": name,
                        "season": season,
                        "langage": langage,
                        "streaming": streaming,
                        "file_name": file_name
                    },
                    "location": exists_result["location"],
                    "day": exists_result.get("day")
                }), 200

            # Ajouter dans anime.json
            success = helpers.add_anime_to_json(
                name=name,
                season=season,
                langage=langage,
                streaming=streaming,
                file_name=file_name,
                day=day
            )

            if not success:
                # Cas où l'ajout échoue pour une autre raison
                return jsonify({
                    "ok": False,
                    "already_exists": False,
                    "error": "Erreur lors de l'ajout de l'anime"
                }), 500

            location = f"auto_download.{day}" if day else "single_download"
            return jsonify({
                "ok": True,
                "already_exists": False,
                "message": f"Anime ajouté avec succès dans {location}",
                "anime": {
                    "name": name,
                    "season": season,
                    "langage": langage,
                    "streaming": streaming,
                    "file_name": file_name
                },
                "location": location,
                "day": day
            }), 200

        except Exception as e:
            return jsonify({"ok": False, "error": f"Erreur lors de l'ajout: {str(e)}"}), 500

    @api_bp.route("/check-anime", methods=["POST"])
    def api_check_anime():
        """Vérifie si un anime existe dans anime.json."""
        data = request.get_json(silent=True) or {}
        anime_url = data.get("anime_url", "").strip()

        if not anime_url:
            return jsonify({"ok": False, "error": "anime_url est obligatoire"}), 400

        try:
            # Déconstruire l'URL
            if "/catalogue/" not in anime_url:
                return jsonify({"ok": False, "error": "URL d'anime invalide"}), 400

            parts = anime_url.rstrip("/").split("/catalogue/")[1].split("/")
            
            if len(parts) < 3:
                return jsonify({"ok": False, "error": "URL d'anime invalide"}), 400

            name = parts[0]
            season_str = parts[1] if len(parts) > 1 else "saison1"
            # Enlever "saison" ou "Saison" du début, mais conserver le reste (y compris les tirets)
            season_match = re.sub(r'^[Ss]aison', '', season_str, flags=re.IGNORECASE)
            
            # Vérifier si la saison contient des lettres après le numéro (ex: saison1hs)
            # Accepter les saisons avec tirets (ex: saison1-2) mais rejeter celles avec lettres
            if re.search(r'^\d+[a-zA-Z]+', season_match):
                return jsonify({
                    "ok": False,
                    "error": "Ce type de saison n'est pas supporté (ex: saison1hs). Veuillez utiliser la version standard (ex: saison1) ou avec tirets (ex: saison1-2)."
                }), 400
            
            # Accepter les saisons simples (1) ou avec tirets (1-2, 3-5, etc.)
            if not season_match or season_match.strip() == "":
                season = "1"
            else:
                season = season_match.strip()  # Conserver le format exact (1-2, 3-5, etc.)
            langage = parts[2] if len(parts) > 2 else "vostfr"

            # Vérifier dans anime.json
            result = helpers.check_anime_in_json(name, season, langage)

            return jsonify({
                "ok": True,
                "exists": result["exists"],
                "day": result["day"],
                "location": result["location"]
            }), 200

        except Exception as e:
            return jsonify({"ok": False, "error": f"Erreur lors de la vérification: {str(e)}"}), 500

    @api_bp.route("/remove-download", methods=["POST"])
    def api_remove_download():
        """Supprime un anime de anime.json."""
        data = request.get_json(silent=True) or {}
        anime_url = data.get("anime_url", "").strip()

        if not anime_url:
            return jsonify({"ok": False, "error": "anime_url est obligatoire"}), 400

        try:
            # Déconstruire l'URL
            if "/catalogue/" not in anime_url:
                return jsonify({"ok": False, "error": "URL d'anime invalide"}), 400

            parts = anime_url.rstrip("/").split("/catalogue/")[1].split("/")
            
            if len(parts) < 3:
                return jsonify({"ok": False, "error": "URL d'anime invalide"}), 400

            name = parts[0]
            season_str = parts[1] if len(parts) > 1 else "saison1"
            # Enlever "saison" ou "Saison" du début, mais conserver le reste (y compris les tirets)
            season_match = re.sub(r'^[Ss]aison', '', season_str, flags=re.IGNORECASE)
            
            # Vérifier si la saison contient des lettres après le numéro (ex: saison1hs)
            # Accepter les saisons avec tirets (ex: saison1-2) mais rejeter celles avec lettres
            if re.search(r'^\d+[a-zA-Z]+', season_match):
                return jsonify({
                    "ok": False,
                    "error": "Ce type de saison n'est pas supporté (ex: saison1hs). Veuillez utiliser la version standard (ex: saison1) ou avec tirets (ex: saison1-2)."
                }), 400
            
            # Accepter les saisons simples (1) ou avec tirets (1-2, 3-5, etc.)
            if not season_match or season_match.strip() == "":
                season = "1"
            else:
                season = season_match.strip()  # Conserver le format exact (1-2, 3-5, etc.)
            langage = parts[2] if len(parts) > 2 else "vostfr"

            # Supprimer de anime.json
            success = helpers.remove_anime_from_json(name, season, langage)

            if not success:
                return jsonify({"ok": False, "error": "Anime non trouvé dans la liste"}), 404

            return jsonify({
                "ok": True,
                "message": "Anime supprimé avec succès"
            }), 200

        except Exception as e:
            return jsonify({"ok": False, "error": f"Erreur lors de la suppression: {str(e)}"}), 500

    @api_bp.route("/theme", methods=["GET"])
    def api_get_theme():
        """Retourne le thème actuel et ses couleurs pour l'extension."""
        from app.sys import FolderConfig, EnvConfig
        import configparser
        
        # Récupérer le thème depuis config.conf
        current_theme = "neon-cyberpunk"  # Valeur par défaut
        try:
            config_path = FolderConfig.find_path(file_name="config.conf")
            if config_path and config_path.exists():
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_path, encoding='utf-8')
                if config.has_section("settings") and config.has_option("settings", "theme"):
                    current_theme = config.get("settings", "theme")
        except Exception:
            pass
        
        theme_colors = get_theme_colors(current_theme)
        
        return jsonify({
            "ok": True,
            "theme": current_theme,
            "colors": theme_colors
        }), 200

    @api_bp.route("/app-info", methods=["GET"])
    def api_get_app_info():
        """Retourne les informations de l'application pour l'extension."""
        from app.sys import FolderConfig
        import configparser
        
        # Récupérer as_Baseurl depuis config.conf
        anime_sama_url = "https://anime-sama.tv"  # Valeur par défaut
        try:
            config_path = FolderConfig.find_path(file_name="config.conf")
            if config_path and config_path.exists():
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_path, encoding='utf-8')
                if config.has_section("scan-option") and config.has_option("scan-option", "as_Baseurl"):
                    anime_sama_url = config.get("scan-option", "as_Baseurl")
        except Exception:
            pass
        
        return jsonify({
            "ok": True,
            "app_name": "Plex Anime Downloader",
            "local_dashboard_port": 5001,
            "anime_sama_url": anime_sama_url
        }), 200

    @api_bp.route("/anime-list", methods=["GET"])
    def api_get_anime_list():
        """Retourne la liste complète de tous les animes téléchargés pour synchronisation du cache."""
        try:
            anime_data = helpers.load_anime_json()
            anime_list = []
            
            # Extraire tous les animes de la structure
            if isinstance(anime_data, list) and len(anime_data) > 0:
                anime_dict = anime_data[0]
                
                # Fonction helper pour ajouter un anime à la liste
                def add_anime(anime_dict_item, day=None, location="single_download"):
                    if isinstance(anime_dict_item, dict):
                        name = anime_dict_item.get("name", "")
                        season = anime_dict_item.get("season", "1")
                        langage = anime_dict_item.get("langage", "vostfr")
                        anime_url = f"/catalogue/{name}/saison{season}/{langage}/"
                        anime_list.append({
                            "url": anime_url,
                            "name": name,
                            "season": season,
                            "langage": langage,
                            "day": day if day and day != "no_day" else None,
                            "location": location
                        })
                
                # Parcourir auto_download
                if "auto_download" in anime_dict:
                    for day, animes in anime_dict["auto_download"].items():
                        if isinstance(animes, list):
                            for anime in animes:
                                add_anime(anime, day, "auto_download")
                
                # Parcourir single_download
                if "single_download" in anime_dict:
                    if isinstance(anime_dict["single_download"], list):
                        for anime in anime_dict["single_download"]:
                            add_anime(anime, None, "single_download")
            
            return jsonify({
                "ok": True,
                "anime_list": anime_list,
                "count": len(anime_list)
            }), 200
            
        except Exception as e:
            return jsonify({
                "ok": False,
                "error": f"Erreur lors de la récupération de la liste: {str(e)}"
            }), 500

    return api_bp

