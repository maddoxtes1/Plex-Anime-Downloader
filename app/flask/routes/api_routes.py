"""
Routes pour l'API JSON (extension navigateur)
"""
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from app.flask.themes import get_theme_colors, get_available_themes


def create_api_blueprint(helpers, queue_manager=None, system=None):
    """
    Crée le blueprint pour les routes API.
    
    Args:
        helpers: Instance de FlaskHelpers
        queue_manager: Instance de queues pour ajouter des téléchargements
        system: Instance de check_sys pour les chemins
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
        if not system:
            return jsonify({"ok": False, "error": "Système non disponible"}), 503

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
            parts = anime_url.rstrip("/").split("/catalogue/")[1].split("/")
            
            if len(parts) < 3:
                return jsonify({"ok": False, "error": "URL d'anime invalide (format attendu: /catalogue/{name}/saison{season}/{langage})"}), 400

            name = parts[0]  # egao-no-taenai-shokuba-desu
            
            # Extraire la saison (saison1 -> 1)
            season_str = parts[1] if len(parts) > 1 else "saison1"
            season_match = season_str.replace("saison", "").replace("Saison", "")
            season = season_match if season_match.isdigit() else "1"
            
            # Extraire le langage
            langage = parts[2] if len(parts) > 2 else "vostfr"
            
            streaming = "anime-sama"
            file_name = "none"

            # Valider le jour si fourni
            valid_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            if day and day not in valid_days:
                day = None  # Si jour invalide, mettre dans single_download

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
                return jsonify({
                    "ok": False,
                    "error": "Cet anime est déjà dans la liste"
                }), 409

            location = f"auto_download.{day}" if day else "single_download"
            return jsonify({
                "ok": True,
                "message": f"Anime ajouté avec succès dans {location}",
                "anime": {
                    "name": name,
                    "season": season,
                    "langage": langage,
                    "streaming": streaming,
                    "file_name": file_name
                }
            }), 200

        except Exception as e:
            return jsonify({"ok": False, "error": f"Erreur lors de l'ajout: {str(e)}"}), 500

    @api_bp.route("/check-anime", methods=["POST"])
    def api_check_anime():
        """Vérifie si un anime existe dans anime.json."""
        if not system:
            return jsonify({"ok": False, "error": "Système non disponible"}), 503

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
            season_match = season_str.replace("saison", "").replace("Saison", "")
            season = season_match if season_match.isdigit() else "1"
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
        if not system:
            return jsonify({"ok": False, "error": "Système non disponible"}), 503

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
            season_match = season_str.replace("saison", "").replace("Saison", "")
            season = season_match if season_match.isdigit() else "1"
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
        if not system:
            return jsonify({"ok": False, "error": "Système non disponible"}), 500
        
        current_theme = system.theme or "neon-cyberpunk"
        theme_colors = get_theme_colors(current_theme)
        
        return jsonify({
            "ok": True,
            "theme": current_theme,
            "colors": theme_colors
        }), 200

    @api_bp.route("/app-info", methods=["GET"])
    def api_get_app_info():
        """Retourne les informations de l'application pour l'extension."""
        return jsonify({
            "ok": True,
            "app_name": "Plex Anime Downloader",
            "local_dashboard_port": 5001,
            "anime_sama_url": "https://anime-sama.eu"
        }), 200

    return api_bp

