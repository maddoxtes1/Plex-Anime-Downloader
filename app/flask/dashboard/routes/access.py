"""
Routes pour la page de connexion (access.html)
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
from werkzeug.security import check_password_hash
from datetime import datetime
from app.flask.dashboard.themes import get_login_page_css
from app.sys import FolderConfig
import configparser


def register_access_routes(local_bp, local_admin_password_hash):
    """
    Enregistre les routes pour la page de connexion.

    Args:
        local_bp: Blueprint Flask
        local_admin_password_hash: Hash du mot de passe admin local
    """

    @local_bp.route("/", methods=["GET", "POST"])
    def local_login():
        """
        Page locale protégée par un seul mot de passe admin (type Vaultwarden).
        """
        if session.get("local_authenticated"):
            return redirect(url_for("local.local_dashboard_search"))

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
                        return redirect(url_for("local.local_dashboard_search"))
                except Exception as e:
                    flash(f"Erreur lors de la vérification du mot de passe: {str(e)}", "error")

        # Récupérer le thème actuel pour la page de connexion
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

    @local_bp.route("/local/logout")
    def local_logout():
        """
        Déconnexion de l'interface locale.
        """
        session.pop("local_authenticated", None)
        session.pop("last_activity", None)
        flash("Vous avez été déconnecté de l'interface locale.", "success")
        return redirect(url_for("local.local_login"))
