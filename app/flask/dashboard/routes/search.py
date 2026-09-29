"""Routes pour la page de recherche"""
from flask import Blueprint, render_template, jsonify, request
from app.flask.dashboard.themes import get_theme_css, get_theme_colors
import configparser
from app.sys import FolderConfig
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging
from app.streaming import search_anime, get_anime_season
from app.sys import universal_logger


def register_search_routes(local_bp):
    """
    Enregistre les routes pour la page de recherche.

    Args:
        local_bp: Blueprint Flask
    """

    @local_bp.route("/search")
    def local_dashboard_search():
        """
        Page de recherche.
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

    @local_bp.route("/api/search", methods=["POST"])
    def api_search():
        """
        Endpoint API pour rechercher des anime sur Anime-sama.

        Extrait tous les liens des catalog cards pour un terme de recherche donné.

        Returns:
            dict: JSON contenant la liste des href des catalog cards
        """
        data = request.get_json()
        search_term = (data.get("query", "").strip().replace(" ", "+"))

        source = data.get("source","anime_sama")
        if source == "anime_sama":
            value = search_anime(value=search_term)
        elif source == "franime":
            return jsonify({"hrefs": None})
        else:
            return jsonify({"error": "Source de recherche invalide."}), 400

        return jsonify({"hrefs": value})


    @local_bp.route("/api/download/add", methods=["POST"])
    def add_download():

        data = request.get_json()

        anime = data.get("anime")
        seasons = data.get("seasons", [])
        source = data.get("source", "anime_sama")

        if not anime:
            return jsonify({"error": "Anime manquant."}), 400

        if not seasons:
            return jsonify({"error": "Aucune saison sélectionnée."}), 400

        if source == "anime-sama":
            url = anime.get("url")
            name = url.split('/catalogue/')[-1].strip('/')



        # Add download logic here
        return jsonify({"success": True,"redirect": "/download"})

    @local_bp.route("/api/download/language", methods=["POST"])
    def language_download():
        data = request.get_json()
        anime = data.get("anime")
        seasons = data.get("seasons", [])
        source = data.get("source", "anime_sama")

        if not anime:
            return jsonify({"error": "Anime manquant."}), 400

        if not seasons:
            return jsonify({"error": "Aucune saison sélectionnée."}), 400

        if source == "anime_sama":
            url = anime.get("url")
            name = url.split('/catalogue/')[-1].strip('/')
            season_language = get_anime_season(anime_name=name, anime_season_number=seasons)
            print(season_language)
            return jsonify(season_language)
        else:
            return jsonify({"error": "Source de recherche invalide."}), 400
