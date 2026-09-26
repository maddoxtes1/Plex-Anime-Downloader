"""
Routes pour la page de recherche
"""
from flask import Blueprint, render_template
from app.flask.dashboard.themes import get_theme_css, get_theme_colors
import configparser
from app.sys import FolderConfig


def register_search_routes(local_bp):
    """
    Enregistre les routes pour la page de recherche.

    Args:
        local_bp: Blueprint Flask
    """

    @local_bp.route("/search")
    def local_dashboard_search():
        """
        Page de recherche vide.
        """
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

        return render_template("search.html", theme_css=theme_css, theme_colors=theme_colors)
