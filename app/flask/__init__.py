from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from app.sys.logger import flask_logger
import sqlite3
import os
import json
import configparser


def create_app(system) -> Flask:
    """
    Crée et configure l'application Flask pour :
    - l'interface locale admin (type Vaultwarden)
    - l'API JSON consommée par l'extension navigateur

    data_path doit correspondre à DATA dans ton conteneur (même valeur que check_sys.data_path).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "templates")
    
    app = Flask(
        __name__,
                template_folder=template_dir,
    )

    log = flask_logger()

    if system:
        data_path = system.data_path
        config_path = system.config_path
        plex_root = system.plex_path
        secret_key = system.app_secret_key
        local_admin_password = system.local_admin_password
    else:
        raise ValueError("system is required to create the app debug: line 51 in flask/__init__.py")

    db_path = os.path.join(data_path, "database", "users.db")

    app.config["SECRET_KEY"] = secret_key

    # Mot de passe admin local (ENV obligatoire en prod)
    local_admin_password = local_admin_password
    app.config["LOCAL_ADMIN_PASSWORD_HASH"] = generate_password_hash(local_admin_password)

    # CORS pour l'extension (API uniquement)
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
    )

    # ------------------------------------------------------------------
    # Helpers internes (DB, config.conf, plex_path.json)
    # ------------------------------------------------------------------

    def get_db_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        # Crée uniquement la DB users, pas les fichiers de config
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        if not os.path.exists(db_path):
            conn = get_db_connection()
            with conn:
                conn.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    );
                    """
                )
            conn.close()
            log.info("Base users.db créée")

    def load_config_conf():
        """
        Lit config.conf et renvoie un dict avec threads, timer, anime_sama, franime.
        Ne crée pas le fichier : il doit déjà exister (créé par ton app Docker).
        """
        cfg = configparser.ConfigParser(allow_no_value=True)
        config_file = os.path.join(config_path, "config.conf")

        if not os.path.exists(config_file):
            # valeurs par défaut si le fichier n'existe pas
            return {
                "threads": 4,
                "timer": 3600,
                "anime_sama": True,
                "franime": False,
            }

        cfg.read(config_file, encoding="utf-8")
        threads = int(cfg.get("settings", "threads", fallback="4"))
        timer = int(cfg.get("settings", "timer", fallback="3600"))
        anime_sama = cfg.get("scan-option", "anime-sama", fallback="True").lower() == "true"
        franime = cfg.get("scan-option", "franime", fallback="False").lower() == "true"
        return {
            "threads": threads,
            "timer": timer,
            "anime_sama": anime_sama,
            "franime": franime,
        }

    def save_config_conf(threads: int, timer: int, anime_sama: bool, franime: bool):
        """
        Réécrit config.conf avec les nouvelles valeurs.
        """
        os.makedirs(config_path, exist_ok=True)
        config_file = os.path.join(config_path, "config.conf")
        cfg = configparser.ConfigParser(allow_no_value=True)
        cfg.add_section("settings")
        cfg.set("settings", "threads", str(threads))
        cfg.set("settings", "timer", str(timer))
        cfg.add_section("scan-option")
        cfg.set("scan-option", "anime-sama", "True" if anime_sama else "False")
        cfg.set("scan-option", "franime", "True" if franime else "False")
        with open(config_file, "w", encoding="utf-8") as f:
            cfg.write(f)

    def load_plex_paths():
        plex_path_file = os.path.join(config_path, "plex_path.json")
        if not os.path.exists(plex_path_file):
            return []
        with open(plex_path_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
        result = []
        for item in data:
            path = item.get("path")
            if not path:
                continue
            languages = item.get("language") or []
            if isinstance(languages, str):
                languages = [languages]
            result.append({"path": path, "language": languages})
        return result

    def save_plex_paths(entries):
        plex_path_file = os.path.join(config_path, "plex_path.json")
        os.makedirs(config_path, exist_ok=True)
        with open(plex_path_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=4, ensure_ascii=False)

    def get_user_by_username(username: str):
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,),
        ).fetchone()
        conn.close()
        return user

    def save_user(username: str, password_hash: str):
        conn = get_db_connection()
        with conn:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password_hash),
            )
        conn.close()

    # Initialisation DB
    init_db()

    # ------------------------------------------------------------------
    # 1) INTERFACE LOCALE (HTML admin)
    # ------------------------------------------------------------------

    @app.route("/", methods=["GET", "POST"])
    def local_login():
        """
        Page locale protégée par un seul mot de passe admin (type Vaultwarden).
        """
        if session.get("local_authenticated"):
            return redirect(url_for("local_dashboard"))

        if request.method == "POST":
            password = (request.form.get("password") or "").strip()
            if not password:
                flash("Veuillez entrer le mot de passe.", "error")
            elif not check_password_hash(app.config["LOCAL_ADMIN_PASSWORD_HASH"], password):
                flash("Mot de passe invalide.", "error")
            else:
                session["local_authenticated"] = True
                flash("Connexion réussie.", "success")
                return redirect(url_for("local_dashboard"))

        return render_template("access.html")

    @app.route("/local/dashboard")
    def local_dashboard():
        """
        Dashboard local :
        - gestion des utilisateurs
        - édition de config.conf
        - édition de plex_path.json
        """
        if not session.get("local_authenticated"):
            flash("Vous devez être connecté avec le mot de passe admin.", "error")
            return redirect(url_for("local_login"))

        conn = get_db_connection()
        users = conn.execute("SELECT username FROM users ORDER BY username").fetchall()
        conn.close()

        cfg = load_config_conf()
        plex_entries = load_plex_paths()

        return render_template(
            "local_dashboard.html",
            users=users,
            config=cfg,
            plex_entries=plex_entries,
            plex_root=plex_root,
            CONFIG_PATH=config_path,
        )

    @app.route("/local/users/create", methods=["POST"])
    def local_create_user():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if not username or not password:
            flash("Nom d'utilisateur et mot de passe requis.", "error")
            return redirect(url_for("local_dashboard"))

        if get_user_by_username(username):
            flash("Cet utilisateur existe déjà.", "error")
            return redirect(url_for("local_dashboard"))

        save_user(username, generate_password_hash(password))
        flash(f"Utilisateur '{username}' créé.", "success")
        return redirect(url_for("local_dashboard"))

    @app.route("/local/users/delete", methods=["POST"])
    def local_delete_user():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        username = (request.form.get("username") or "").strip()
        if not username:
            flash("Aucun utilisateur spécifié.", "error")
            return redirect(url_for("local_dashboard"))

        conn = get_db_connection()
        with conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.close()
        flash(f"Utilisateur '{username}' supprimé.", "success")
        return redirect(url_for("local_dashboard"))

    @app.route("/local/config", methods=["POST"])
    def local_update_config():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        try:
            threads = int(request.form.get("threads") or "4")
            timer = int(request.form.get("timer") or "3600")
        except ValueError:
            flash("Threads et timer doivent être des nombres entiers.", "error")
            return redirect(url_for("local_dashboard"))

        anime_sama = request.form.get("anime_sama") == "on"
        franime = request.form.get("franime") == "on"

        save_config_conf(threads, timer, anime_sama, franime)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local_dashboard"))

    @app.route("/local/plex/add", methods=["POST"])
    def local_plex_add():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()
        create_folder = request.form.get("create_folder") == "on"

        if not path_name:
            flash("Le nom du dossier (path) est obligatoire.", "error")
            return redirect(url_for("local_dashboard"))

        languages = [
            lang.strip()
            for lang in languages_raw.split(",")
            if lang.strip()
        ]

        entries = load_plex_paths()

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
            return redirect(url_for("local_dashboard"))

        # création du dossier physique si demandé
        if create_folder:
            try:
                os.makedirs(os.path.join(plex_root, path_name), exist_ok=True)
            except OSError as e:
                flash(f"Erreur lors de la création du dossier: {e}", "error")
                return redirect(url_for("local_dashboard"))

        # mise à jour / ajout
        updated = False
        for item in entries:
            if item["path"] == path_name:
                item["language"] = languages
                updated = True
                break
        if not updated:
            entries.append({"path": path_name, "language": languages})

        save_plex_paths(entries)
        flash("Configuration plex_path.json mise à jour.", "success")
        return redirect(url_for("local_dashboard"))

    @app.route("/local/plex/update", methods=["POST"])
    def local_plex_update():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        old_path = (request.form.get("old_path") or "").strip()
        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()
        if not old_path or not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local_dashboard"))

        languages = [
            lang.strip()
            for lang in languages_raw.split(",")
            if lang.strip()
        ]

        entries = load_plex_paths()

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
            return redirect(url_for("local_dashboard"))

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
            save_plex_paths(entries)
            flash("Entrée mise à jour.", "success")
        return redirect(url_for("local_dashboard"))

    @app.route("/local/plex/delete", methods=["POST"])
    def local_plex_delete():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local_login"))

        path_name = (request.form.get("path") or "").strip()
        if not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local_dashboard"))

        entries = load_plex_paths()
        new_entries = [e for e in entries if e["path"] != path_name]
        save_plex_paths(new_entries)
        flash(
            f"Entrée '{path_name}' supprimée (fichier non supprimé sur le disque).",
            "success",
        )
        return redirect(url_for("local_dashboard"))

    @app.route("/local/logout")
    def local_logout():
        """
        Déconnexion de l'interface locale.
        """
        session.pop("local_authenticated", None)
        flash("Vous avez été déconnecté de l'interface locale.", "success")
        return redirect(url_for("local_login"))

    # ---------------------------------------------------------
    # 2) API POUR L'EXTENSION (JSON)
    # ---------------------------------------------------------

    @app.route("/api/ping", methods=["GET"])
    def api_ping():
        """Permet à l'extension de tester la connexion au serveur."""
        return jsonify({"ok": True, "message": "pong"}), 200

    @app.route("/api/login", methods=["POST"])
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

        user = get_user_by_username(username)
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"ok": False, "error": "identifiants invalides"}), 401

        return jsonify({"ok": True, "user": username}), 200

    @app.route("/api/dashboard", methods=["GET"])
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

    log.info("Application Flask initialisée (admin local + API extension)")
    return app
