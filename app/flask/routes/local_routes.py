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
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil


def create_local_blueprint(helpers, app_config, plex_root, config_path):
    """
    Crée le blueprint pour les routes locales.
    
    Args:
        helpers: Instance de FlaskHelpers
        app_config: Configuration de l'app Flask (pour SECRET_KEY, etc.)
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
    """
    local_bp = Blueprint("local", __name__)

    @local_bp.route("/", methods=["GET", "POST"])
    def local_login():
        """
        Page locale protégée par un seul mot de passe admin (type Vaultwarden).
        """
        if session.get("local_authenticated"):
            return redirect(url_for("local.local_dashboard"))

        if request.method == "POST":
            password = (request.form.get("password") or "").strip()
            if not password:
                flash("Veuillez entrer le mot de passe.", "error")
            elif not check_password_hash(app_config["LOCAL_ADMIN_PASSWORD_HASH"], password):
                flash("Mot de passe invalide.", "error")
            else:
                session["local_authenticated"] = True
                flash("Connexion réussie.", "success")
                return redirect(url_for("local.local_dashboard"))

        return render_template("access.html")

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

        return render_template(
            "local_dashboard.html",
            users=users,
            config=cfg,
            plex_entries=plex_entries,
            plex_root=plex_root,
            CONFIG_PATH=config_path,
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
            return redirect(url_for("local.local_dashboard"))

        if helpers.get_user_by_username(username):
            flash("Cet utilisateur existe déjà.", "error")
            return redirect(url_for("local.local_dashboard"))

        helpers.save_user(username, generate_password_hash(password))
        flash(f"Utilisateur '{username}' créé.", "success")
        return redirect(url_for("local.local_dashboard"))

    @local_bp.route("/local/users/delete", methods=["POST"])
    def local_delete_user():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        username = (request.form.get("username") or "").strip()
        if not username:
            flash("Aucun utilisateur spécifié.", "error")
            return redirect(url_for("local.local_dashboard"))

        conn = helpers.get_db_connection()
        with conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.close()
        flash(f"Utilisateur '{username}' supprimé.", "success")
        return redirect(url_for("local.local_dashboard"))

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
            return redirect(url_for("local.local_dashboard"))

        anime_sama = request.form.get("anime_sama") == "on"
        franime = request.form.get("franime") == "on"

        helpers.save_config_conf(threads, timer, anime_sama, franime)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local.local_dashboard"))

    @local_bp.route("/local/plex/add", methods=["POST"])
    def local_plex_add():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()

        if not path_name:
            flash("Le nom du dossier (path) est obligatoire.", "error")
            return redirect(url_for("local.local_dashboard"))

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
            return redirect(url_for("local.local_dashboard"))

        # création du dossier physique si demandé
        try:
            import os
            os.makedirs(os.path.join(plex_root, path_name), exist_ok=True)
        except OSError as e:
            flash(f"Erreur lors de la création du dossier: {e}", "error")
            return redirect(url_for("local.local_dashboard"))

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
        return redirect(url_for("local.local_dashboard"))

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
            return redirect(url_for("local.local_dashboard"))

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
            return redirect(url_for("local.local_dashboard"))

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
        return redirect(url_for("local.local_dashboard"))

    @local_bp.route("/local/plex/delete", methods=["POST"])
    def local_plex_delete():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        if not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local.local_dashboard"))

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
        
        return redirect(url_for("local.local_dashboard"))

    @local_bp.route("/local/logout")
    def local_logout():
        """
        Déconnexion de l'interface locale.
        """
        session.pop("local_authenticated", None)
        flash("Vous avez été déconnecté de l'interface locale.", "success")
        return redirect(url_for("local.local_login"))

    return local_bp

