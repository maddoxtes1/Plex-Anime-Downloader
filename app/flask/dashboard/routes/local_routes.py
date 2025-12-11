"""
Routes pour l'interface locale admin (HTML)
"""
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    jsonify,
    Response,
    stream_with_context,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import shutil
import zipfile
import tempfile
import configparser
import json
import time
from app.flask.dashboard.themes import get_theme_css, get_available_themes, get_login_page_css, get_theme_colors
import threading
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def create_local_blueprint(helpers, app_config, plex_root, config_path, local_admin_password_hash):
    """
    Crée le blueprint pour les routes locales.
    
    Args:
        helpers: Instance de FlaskHelpers
        app_config: Configuration de l'app Flask (pour SECRET_KEY, etc.)
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
        local_admin_password_hash: Hash du mot de passe admin local
    """
    local_bp = Blueprint("local", __name__)
    
    
    
    # Durée d'expiration de session : 5 minutes
    SESSION_TIMEOUT = timedelta(minutes=5)
    
    @local_bp.before_request
    def check_session_expiry():
        """
        Vérifie si la session a expiré (5 minutes d'inactivité).
        """
        if session.get("local_authenticated"):
            last_activity = session.get("last_activity")
            if last_activity:
                try:
                    last_activity_dt = datetime.fromisoformat(last_activity)
                    if datetime.now() - last_activity_dt > SESSION_TIMEOUT:
                        # Session expirée
                        session.pop("local_authenticated", None)
                        session.pop("last_activity", None)
                        flash("Votre session a expiré. Veuillez vous reconnecter.", "error")
                        return redirect(url_for("local.local_login"))
                except (ValueError, TypeError):
                    # Format invalide, réinitialiser
                    session.pop("local_authenticated", None)
                    session.pop("last_activity", None)
            
            # Mettre à jour la dernière activité
            session["last_activity"] = datetime.now().isoformat()
            session.permanent = True

    @local_bp.route("/", methods=["GET", "POST"])
    def local_login():
        """
        Page locale protégée par un seul mot de passe admin (type Vaultwarden).
        """
        if session.get("local_authenticated"):
            return redirect(url_for("local.local_dashboard") + "#news")

        if request.method == "POST":
            password = (request.form.get("password") or "").strip()
            if not password:
                flash("Veuillez entrer le mot de passe.", "error")
            else:
                try:
                    is_valid = check_password_hash(local_admin_password_hash, password)
                    if not is_valid:
                        flash("Mot de passe invalide.", "error")
                    else:
                        session["local_authenticated"] = True
                        session["last_activity"] = datetime.now().isoformat()
                        session.permanent = True
                        flash("Connexion réussie.", "success")
                        return redirect(url_for("local.local_dashboard") + "#news")
                except Exception as e:
                    flash(f"Erreur lors de la vérification du mot de passe: {str(e)}", "error")

        # Récupérer le thème actuel pour la page de connexion
        from app.sys import FolderConfig
        import configparser
        
        current_theme = "neon-cyberpunk"  # Valeur par défaut
        try:
            config_file = FolderConfig.find_path(file_name="config.conf")
            if config_file and config_file.exists():
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_file, encoding='utf-8')
                if config.has_section("settings") and config.has_option("settings", "theme"):
                    current_theme = config.get("settings", "theme")
        except Exception:
            pass
        
        login_theme_css = get_login_page_css(current_theme)

        return render_template("access.html", theme_css=login_theme_css)

    @local_bp.route("/local/dashboard")
    def local_dashboard():
        """
        Dashboard local :
        - gestion des utilisateurs
        - édition de config.conf
        - édition de plex_path.json
        """
        if not session.get("local_authenticated"):
            flash("Vous devez être connecté avec le mot de passe admin.", "error")
            return redirect(url_for("local.local_login"))

        conn = helpers.get_db_connection()
        users = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
        conn.close()

        cfg = helpers.load_config_conf()
        plex_entries = helpers.load_plex_paths()
        
        # Récupérer le thème actuel
        from app.sys import FolderConfig, EnvConfig
        import configparser
        
        current_theme = "neon-cyberpunk"  # Valeur par défaut
        try:
            config_file = FolderConfig.find_path(file_name="config.conf")
            if config_file and config_file.exists():
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_file, encoding='utf-8')
                if config.has_section("settings") and config.has_option("settings", "theme"):
                    current_theme = config.get("settings", "theme")
        except Exception:
            pass
        
        theme_css = get_theme_css(current_theme)
        theme_colors = get_theme_colors(current_theme)
        available_themes = get_available_themes()
        
        # Récupérer la liste des fichiers de logs
        log_files = []
        logs_path = FolderConfig.find_path(folder_name="logs")
        if logs_path and os.path.exists(logs_path):
            for file in os.listdir(logs_path):
                if file.endswith('.log'):
                    file_path = os.path.join(logs_path, file)
                    file_size = os.path.getsize(file_path)
                    log_files.append({
                        'name': file,
                        'size': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    })
        
        # Récupérer les actualités depuis le serveur externe et enregistrer le serveur
        news_list = []
        news_error = None
        news_disabled = False
        
        # Vérifier si news est activé dans config.conf
        news_enabled = True
        try:
            config_file = FolderConfig.find_path(file_name="config.conf")
            if config_file and config_file.exists():
                config = configparser.ConfigParser(allow_no_value=True)
                config.read(config_file, encoding='utf-8')
                if config.has_section('settings') and config.has_option('settings', 'news'):
                    news_enabled = config.get('settings', 'news', fallback='True').lower() == 'true'
                    news_disabled = not news_enabled
        except Exception:
            pass  # En cas d'erreur, utiliser True par défaut
        
        # Ne faire la requête que si news est activé
        if news_enabled:
            try:
                import requests
                news_api_url = EnvConfig.get_env("news_api_url")
                
                # Préparer les headers pour le tracking
                headers = {}
                # Lire Server_ID depuis .env
                try:
                    env_file = FolderConfig.find_path(file_name=".env")
                    if env_file and env_file.exists():
                        with open(env_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('Server_ID='):
                                    server_id = line.split('=', 1)[1].strip()
                                    if server_id and server_id != 'none':
                                        headers["X-Server-ID"] = server_id
                                    break
                except Exception:
                    pass
                # Lire Version depuis .env ou utiliser la version par défaut
                try:
                    env_file = FolderConfig.find_path(file_name=".env")
                    version = None
                    if env_file and env_file.exists():
                        with open(env_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('Version='):
                                    version = line.split('=', 1)[1].strip()
                                    break
                    if not version:
                        version = EnvConfig.get_env("plex_anime_downloader_V")
                    if version:
                        headers["X-Server-Version"] = version
                except Exception:
                    pass
                
                # Faire la requête avec les headers de tracking
                response = requests.get(news_api_url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        news_list = data.get("news", [])
                        # Nettoyer les espaces en début et fin de chaque news
                        for news_item in news_list:
                            if isinstance(news_item, dict) and "content" in news_item:
                                if isinstance(news_item["content"], str):
                                    content = news_item["content"]
                                    # Supprimer tous les espaces/retours à la ligne en début et fin
                                    content = content.strip()
                                    # Supprimer les lignes vides en début et fin
                                    lines = content.split('\n')
                                    # Supprimer les lignes vides au début
                                    while lines and not lines[0].strip():
                                        lines.pop(0)
                                    # Supprimer les lignes vides à la fin
                                    while lines and not lines[-1].strip():
                                        lines.pop()
                                    # Supprimer les espaces en début de la première ligne
                                    if lines:
                                        lines[0] = lines[0].lstrip()
                                    content = '\n'.join(lines).strip()
                                    
                                    # Convertir le Markdown en HTML si disponible
                                    if MARKDOWN_AVAILABLE:
                                        try:
                                            # Utiliser markdown avec extensions pour le support complet
                                            md = markdown.Markdown(extensions=['extra', 'nl2br', 'fenced_code'])
                                            news_item["content"] = md.convert(content)
                                            news_item["content_is_html"] = True
                                        except Exception:
                                            # En cas d'erreur, garder le contenu original
                                            news_item["content"] = content
                                            news_item["content_is_html"] = False
                                    else:
                                        news_item["content"] = content
                                        news_item["content_is_html"] = False
                    else:
                        news_error = data.get("error", "Erreur inconnue")
                else:
                    news_error = f"Erreur HTTP {response.status_code}"
            except Exception as e:
                news_error = f"Impossible de récupérer les actualités: {str(e)}"
        else:
            # Si news est désactivé, ne pas faire de requête
            news_list = []
            news_error = None

        return render_template(
            "local_dashboard.html",
            users=users,
            config=cfg,
            plex_entries=plex_entries,
            plex_root=plex_root,
            CONFIG_PATH=config_path,
            theme_css=theme_css,
            theme_colors=theme_colors,
            current_theme=current_theme,
            available_themes=available_themes,
            log_files=log_files,
            logs_path=str(logs_path) if logs_path else None,
            news_list=news_list,
            news_error=news_error,
            news_disabled=news_disabled,
        )

    @local_bp.route("/local/users/create", methods=["POST"])
    def local_create_user():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if not username or not password:
            flash("Nom d'utilisateur et mot de passe requis.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        if helpers.get_user_by_username(username):
            flash("Cet utilisateur existe déjà.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        helpers.save_user(username, generate_password_hash(password))
        flash(f"Utilisateur '{username}' créé.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/users/delete", methods=["POST"])
    def local_delete_user():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        username = (request.form.get("username") or "").strip()
        if not username:
            flash("Aucun utilisateur spécifié.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        conn = helpers.get_db_connection()
        with conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.close()
        flash(f"Utilisateur '{username}' supprimé.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/config", methods=["POST"])
    def local_update_config():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        try:
            threads = int(request.form.get("threads") or "4")
            timer = int(request.form.get("timer") or "3600")
        except ValueError:
            flash("Threads et timer doivent être des nombres entiers.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        anime_sama = request.form.get("anime_sama") == "on"
        franime = request.form.get("franime") == "on"
        news = request.form.get("news") == "on"
        log_level = request.form.get("log_level", "INFO").strip()

        helpers.save_config_conf(threads, timer, anime_sama, franime, news=news, log_level=log_level)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/theme", methods=["POST"])
    def local_update_theme():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        theme_name = (request.form.get("theme") or "").strip()
        if not theme_name:
            flash("Thème manquant.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        # Vérifier que le thème existe
        available_themes = get_available_themes()
        if theme_name not in available_themes:
            flash("Thème invalide.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        # Sauvegarder le thème dans config.conf
        from app.sys import FolderConfig
        config_file = FolderConfig.find_path(file_name="config.conf")
        if config_file and config_file.exists():
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(config_file, encoding='utf-8')
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'theme', theme_name)
            
            with open(config_file, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
        
        flash(f"Thème changé pour '{available_themes[theme_name]}'.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/logs/list", methods=["GET"])
    def local_logs_list():
        """Retourne la liste des fichiers de logs"""
        if not session.get("local_authenticated"):
            return jsonify({"ok": False, "error": "Non autorisé"}), 401
        
        from app.sys import FolderConfig
        logs_path = FolderConfig.find_path(folder_name="logs")
        if not logs_path:
            return jsonify({"ok": False, "error": "Chemin des logs non disponible"}), 500
        log_files = []
        if os.path.exists(logs_path):
            for file in os.listdir(logs_path):
                if file.endswith('.log'):
                    file_path = os.path.join(logs_path, file)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        log_files.append({
                            'name': file,
                            'size': file_size,
                            'size_mb': round(file_size / (1024 * 1024), 2)
                        })
        
        return jsonify({"ok": True, "files": log_files}), 200

    @local_bp.route("/local/logs/view/<filename>", methods=["GET"])
    def local_logs_view(filename):
        """Retourne le contenu d'un fichier de log"""
        if not session.get("local_authenticated"):
            return jsonify({"ok": False, "error": "Non autorisé"}), 401
        
        from app.sys import FolderConfig
        logs_path = FolderConfig.find_path(folder_name="logs")
        if not logs_path:
            return jsonify({"ok": False, "error": "Chemin des logs non disponible"}), 500
        
        # Sécuriser le nom de fichier
        filename = os.path.basename(filename)
        if not filename.endswith('.log'):
            return jsonify({"ok": False, "error": "Fichier invalide"}), 400
        file_path = os.path.join(logs_path, filename)
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({"ok": False, "error": "Fichier non trouvé"}), 404
        
        try:
            # Lire les dernières lignes (dernières 1000 lignes pour performance)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Prendre les 1000 dernières lignes
                lines = lines[-1000:] if len(lines) > 1000 else lines
                content = ''.join(lines)
            
            return jsonify({
                "ok": True,
                "filename": filename,
                "content": content,
                "total_lines": len(lines)
            }), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @local_bp.route("/local/logs/stream/<filename>", methods=["GET"])
    def local_logs_stream(filename):
        """Stream les logs en temps réel (Server-Sent Events)"""
        if not session.get("local_authenticated"):
            return jsonify({"ok": False, "error": "Non autorisé"}), 401
        
        from app.sys import FolderConfig
        logs_path = FolderConfig.find_path(folder_name="logs")
        if not logs_path:
            return jsonify({"ok": False, "error": "Chemin des logs non disponible"}), 500
        
        # Gérer les logs Docker
        if filename == "docker":
            return local_logs_stream_docker()
        
        # Sécuriser le nom de fichier
        filename = os.path.basename(filename)
        if not filename.endswith('.log'):
            return jsonify({"ok": False, "error": "Fichier invalide"}), 400
        file_path = os.path.join(logs_path, filename)
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return jsonify({"ok": False, "error": "Fichier non trouvé"}), 404
        
        def generate():
            last_position = os.path.getsize(file_path)
            while True:
                try:
                    current_size = os.path.getsize(file_path)
                    if current_size > last_position:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_position)
                            new_content = f.read()
                            if new_content:
                                yield f"data: {json.dumps({'content': new_content})}\n\n"
                            last_position = current_size
                    elif current_size < last_position:
                        # Fichier tronqué ou réinitialisé
                        last_position = 0
                    time.sleep(0.5)  # Vérifier toutes les 0.5 secondes
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    break
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    def local_logs_stream_docker():
        """Stream les logs de l'application en temps réel (tous les fichiers de logs combinés)"""
        from app.sys import FolderConfig
        logs_path = FolderConfig.find_path(folder_name="logs")
        if not logs_path:
            def generate_error():
                yield f"data: {json.dumps({'error': 'Chemin des logs non disponible'})}\n\n"
            return Response(
                stream_with_context(generate_error()),
                mimetype='text/event-stream',
                headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
            )
        log_files = ['sys.log', 'flask.log', 'download.log', 'queue.log', 'anime-sama.log', 'franime.log']
        
        def generate():
            file_positions = {}
            
            try:
                # Initialiser les positions pour tous les fichiers existants
                for log_file in log_files:
                    file_path = os.path.join(logs_path, log_file)
                    if os.path.exists(file_path):
                        try:
                            file_positions[log_file] = os.path.getsize(file_path)
                        except Exception:
                            file_positions[log_file] = 0
                
                if not file_positions:
                    yield f"data: {json.dumps({'error': 'Aucun fichier de log trouvé'})}\n\n"
                    return
                
                # Envoyer un message de démarrage
                start_msg = '=== Démarrage du streaming des logs ===\n'
                yield f"data: {json.dumps({'content': start_msg})}\n\n"
                
                # Streamer les nouveaux logs de tous les fichiers
                while True:
                    any_new_content = False
                    for log_file in list(file_positions.keys()):
                        file_path = os.path.join(logs_path, log_file)
                        
                        if not os.path.exists(file_path):
                            # Fichier supprimé, retirer de la liste
                            del file_positions[log_file]
                            continue
                        
                        try:
                            current_size = os.path.getsize(file_path)
                            last_position = file_positions[log_file]
                            
                            if current_size > last_position:
                                # Nouveau contenu disponible
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    f.seek(last_position)
                                    new_content = f.read()
                                    if new_content:
                                        # Préfixer avec le nom du fichier pour identifier la source
                                        lines = new_content.split('\n')
                                        for line in lines:
                                            if line.strip():
                                                prefixed_line = f"[{log_file}] {line}\n"
                                                yield f"data: {json.dumps({'content': prefixed_line})}\n\n"
                                                any_new_content = True
                                file_positions[log_file] = current_size
                            elif current_size < last_position:
                                # Fichier tronqué ou réinitialisé
                                file_positions[log_file] = 0
                        except Exception as e:
                            # Erreur lors de la lecture, continuer avec les autres fichiers
                            pass
                    
                    if not any_new_content:
                        time.sleep(0.5)  # Attendre 0.5 seconde si pas de nouveau contenu
                    else:
                        time.sleep(0.1)  # Attendre moins longtemps si on a du nouveau contenu
                        
            except Exception as e:
                error_msg = f"Erreur lors du streaming: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    @local_bp.route("/local/plex/add", methods=["POST"])
    def local_plex_add():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()

        if not path_name:
            flash("Le nom du dossier (path) est obligatoire.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        languages = [
            lang.strip()
            for lang in languages_raw.split(",")
            if lang.strip()
        ]

        entries = helpers.load_plex_paths()

        # vérifier qu'aucun autre path n'a déjà ces langues
        used = {}
        for item in entries:
            for lang in item.get("language", []):
                used.setdefault(lang, []).append(item["path"])
        conflicts = []
        for lang in languages:
            paths_for_lang = used.get(lang, [])
            if paths_for_lang:
                conflicts.append(f"{lang} (déjà dans: {', '.join(paths_for_lang)})")
        if conflicts:
            flash(
                "Impossible d'ajouter ce chemin : certains langages sont déjà utilisés : "
                + "; ".join(conflicts),
                "error",
            )
            return redirect(url_for("local.local_dashboard") + "#settings")

        # création du dossier physique si demandé
        try:
            import os
            os.makedirs(os.path.join(plex_root, path_name), exist_ok=True)
        except OSError as e:
            flash(f"Erreur lors de la création du dossier: {e}", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        # mise à jour / ajout
        updated = False
        for item in entries:
            if item["path"] == path_name:
                item["language"] = languages
                updated = True
                break
        if not updated:
            entries.append({"path": path_name, "language": languages})

        helpers.save_plex_paths(entries)
        flash("Configuration plex_path.json mise à jour.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/plex/update", methods=["POST"])
    def local_plex_update():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        old_path = (request.form.get("old_path") or "").strip()
        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()
        if not old_path or not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        languages = [
            lang.strip()
            for lang in languages_raw.split(",")
            if lang.strip()
        ]

        entries = helpers.load_plex_paths()

        # vérifier qu'aucun autre path n'a déjà ces langues
        used = {}
        for item in entries:
            path = item["path"]
            for lang in item.get("language", []):
                used.setdefault(lang, []).append(path)
        conflicts = []
        for lang in languages:
            paths_for_lang = [
                p for p in used.get(lang, []) if p != old_path
            ]
            if paths_for_lang:
                conflicts.append(f"{lang} (déjà dans: {', '.join(paths_for_lang)})")
        if conflicts:
            flash(
                "Impossible de mettre à jour cette entrée : certains langages sont déjà utilisés : "
                + "; ".join(conflicts),
                "error",
            )
            return redirect(url_for("local.local_dashboard") + "#settings")

        found = False
        for item in entries:
            if item["path"] == old_path:
                item["path"] = path_name
                item["language"] = languages
                found = True
                break

        if not found:
            flash("Entrée introuvable.", "error")
        else:
            helpers.save_plex_paths(entries)
            flash("Entrée mise à jour.", "success")
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/plex/delete", methods=["POST"])
    def local_plex_delete():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        if not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        # Supprimer le dossier physique s'il existe
        folder_path = os.path.join(plex_root, path_name)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            try:
                shutil.rmtree(folder_path)
                flash(
                    f"Entrée '{path_name}' et dossier supprimés avec succès.",
                    "success",
                )
            except OSError as e:
                flash(
                    f"Entrée '{path_name}' supprimée, mais erreur lors de la suppression du dossier: {e}",
                    "error",
                )
        else:
            # Supprimer seulement l'entrée JSON si le dossier n'existe pas
            flash(
                f"Entrée '{path_name}' supprimée (dossier non trouvé sur le disque).",
                "success",
            )

        # Supprimer l'entrée du JSON
        entries = helpers.load_plex_paths()
        new_entries = [e for e in entries if e["path"] != path_name]
        helpers.save_plex_paths(new_entries)
        
        return redirect(url_for("local.local_dashboard") + "#settings")

    @local_bp.route("/local/logout")
    def local_logout():
        """
        Déconnexion de l'interface locale.
        """
        session.pop("local_authenticated", None)
        session.pop("last_activity", None)
        flash("Vous avez été déconnecté de l'interface locale.", "success")
        return redirect(url_for("local.local_login"))

    @local_bp.route("/local/extension/download")
    def local_download_extension():
        """
        Télécharge l'extension Chrome au format ZIP.
        """
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        # Chemin vers le dossier extension
        # Depuis app/flask/dashboard/routes/local_routes.py, remonter de 5 niveaux pour arriver à la racine
        current_file = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))
        extension_dir = os.path.join(base_dir, "extension")
        
        if not os.path.exists(extension_dir):
            flash("Le dossier extension est introuvable.", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")

        # Créer un fichier ZIP temporaire
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_file.close()

        try:
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Liste des fichiers à inclure dans l'extension
                extension_files = [
                    "manifest.json",
                    "popup.html",
                    "popup.js",
                    "content.js",
                    "content.css",
                    "icon.png",
                ]
                
                for filename in extension_files:
                    file_path = os.path.join(extension_dir, filename)
                    if os.path.exists(file_path):
                        zipf.write(file_path, filename)
                    else:
                        flash(f"Fichier manquant: {filename}", "error")

            return send_file(
                temp_file.name,
                mimetype='application/zip',
                as_attachment=True,
                download_name='anime-downloader-extension.zip'
            )
        except Exception as e:
            flash(f"Erreur lors de la création du ZIP: {e}", "error")
            return redirect(url_for("local.local_dashboard") + "#settings")
        finally:
            # Nettoyer le fichier temporaire après l'envoi
            if os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    return local_bp

