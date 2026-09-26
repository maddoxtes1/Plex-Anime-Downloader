"""
Fonctions communes partagées entre les différentes routes du dashboard
"""
from datetime import datetime, timedelta
from flask import session, redirect, url_for, flash, render_template
import os
import configparser
from app.flask.dashboard.themes import get_theme_css, get_theme_colors, get_available_themes
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def check_session_expiry(local_bp, SESSION_TIMEOUT):
    """
    Décorateur pour vérifier si la session a expiré (5 minutes d'inactivité).
    """
    @local_bp.before_request
    def check_session():
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


def prepare_dashboard_data(helpers, plex_root, config_path):
    """
    Prépare les données communes pour toutes les pages du dashboard

    Args:
        helpers: Instance de FlaskHelpers
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration

    Returns:
        dict: Dictionnaire avec toutes les données communes
    """

    cfg = helpers.load_config_conf()
    plex_entries = helpers.load_plex_paths()

    # Récupérer le thème actuel depuis le fichier config.conf
    from app.sys import FolderConfig, EnvConfig
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

    return {
        'config': cfg,
        'plex_entries': plex_entries,
        'plex_root': plex_root,
        'CONFIG_PATH': config_path,
        'theme_css': theme_css,
        'theme_colors': theme_colors,
        'current_theme': current_theme,
        'available_themes': available_themes,
        'log_files': log_files,
        'logs_path': str(logs_path) if logs_path else None,
    }
