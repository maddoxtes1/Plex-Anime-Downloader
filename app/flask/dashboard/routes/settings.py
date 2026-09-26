"""
Routes pour la page Paramètres (settings.html)
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
from werkzeug.security import generate_password_hash
import os
import shutil
import configparser
from app.flask.dashboard.routes.common import prepare_dashboard_data
from app.flask.dashboard.themes import get_available_themes
from app.sys import FolderConfig


def register_settings_routes(local_bp, helpers, plex_root, config_path):
    """
    Enregistre les routes pour la page Paramètres.

    Args:
        local_bp: Blueprint Flask
        helpers: Instance de FlaskHelpers
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
    """

    @local_bp.route("/settings")
    def local_dashboard_settings():
        """Page Paramètres"""
        if not session.get("local_authenticated"):
            flash("Vous devez être connecté avec le mot de passe admin.", "error")
            return redirect(url_for("local.local_login"))

        data = prepare_dashboard_data(helpers, plex_root, config_path)
        return render_template("settings.html", **data)

    @local_bp.route("/local/flaresolver", methods=["POST"])
    def local_update_flaresolver():
            """
            Sauvegarde les paramètres système, FlareSolver, Anime-Sama et Franime.
            Utilise le nouveau système de configuration via ConfigManager.
            """
            if not session.get("local_authenticated"):
                flash("Non autorisé.", "error")
                return redirect(url_for("local.local_login"))

            # Validation des paramètres numériques
            # FlareSolver
            flaresolver_host = request.form.get("flaresolver_host")
            flaresolver_port = request.form.get("flaresolver_port")
            use_flaresolver = bool(request.form.get("use_flaresolver"))

            helpers.save_config_conf(flaresolver_host=flaresolver_host, flaresolver_port=flaresolver_port, use_flaresolver=use_flaresolver)
            flash("Configuration sauvegardée.", "success")
            return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/anime-sama", methods=["POST"])
    def local_update_anime_sama():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        anime_sama_auto_delete = bool(request.form.get("anime_sama_auto_delete"))
        anime_sama_base_url = request.form.get("anime_sama_base_url") or "https://anime-sama.tv"
        anime_sama = bool(request.form.get("anime_sama"))

        if not anime_sama_base_url.startswith(("http://", "https://")):
            flash(f"L'URL {url_name} doit commencer par http:// ou https://", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        helpers.save_config_conf(anime_sama_auto_delete=anime_sama_auto_delete, anime_sama_base_url=anime_sama_base_url, anime_sama=anime_sama)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/franime", methods=["POST"])
    def local_update_franime():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        franime_base_url = request.form.get("franime_base_url") or "https://franime.fr"
        franime_api_base_url = request.form.get("franime_api_base_url") or "https://api.franime.fr"
        franime_auto_delete = bool(request.form.get("franime_auto_delete"))
        franime = bool(request.form.get("franime"))

        if not franime_base_url.startswith(("http://", "https://")):
            flash(f"L'URL {url_name} doit commencer par http:// ou https://", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        if not franime_api_base_url.startswith(("http://", "https://")):
            flash(f"L'URL {url_name} doit commencer par http:// ou https://", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        helpers.save_config_conf(franime_base_url=franime_base_url, franime_api_base_url=franime_api_base_url, franime_auto_delete=franime_auto_delete, franime=franime)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/config", methods=["POST"])
    def local_update_config():
        """
        Sauvegarde les paramètres système, FlareSolver, Anime-Sama et Franime.
        Utilise le nouveau système de configuration via ConfigManager.
        """
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        # Validation des paramètres numériques
        try:
            threads = int(request.form.get("threads") or "4")
            timer = int(request.form.get("timer") or "3600")
        except ValueError:
            flash("Threads et timer doivent être des nombres entiers.", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        # Récupération de toutes les valeurs du formulaire
        log_level = request.form.get("log_level", "INFO").strip()

        helpers.save_config_conf(threads=threads, timer=timer, log_level=log_level)
        flash("Configuration sauvegardée.", "success")
        return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/theme", methods=["POST"])
    def local_update_theme():
        """
        Change le thème du dashboard.
        Utilise le système de configuration unifié.
        """
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        theme_name = (request.form.get("theme") or "").strip()
        if not theme_name:
            flash("Thème manquant.", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        # Vérifier que le thème existe
        available_themes = get_available_themes()
        if theme_name not in available_themes:
            flash("Thème invalide.", "error")
            return redirect(url_for("local.local_dashboard_settings"))

        # Sauvegarder le thème via le système unifié de configuration
        helpers.save_config_conf(theme=theme_name)
        flash(f"Thème changé pour '{available_themes[theme_name]}'.", "success")
        return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/plex/add", methods=["POST"])
    def local_plex_add():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        languages_raw = (request.form.get("languages") or "").strip()

        if not path_name:
            flash("Le nom du dossier (path) est obligatoire.", "error")
            return redirect(url_for("local.local_dashboard_settings"))

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
            return redirect(url_for("local.local_dashboard_settings"))

        # création du dossier physique si demandé
        try:
            os.makedirs(os.path.join(plex_root, path_name), exist_ok=True)
        except OSError as e:
            flash(f"Erreur lors de la création du dossier: {e}", "error")
            return redirect(url_for("local.local_dashboard_settings"))

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
        return redirect(url_for("local.local_dashboard_settings"))

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
            return redirect(url_for("local.local_dashboard_settings"))

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
            return redirect(url_for("local.local_dashboard_settings"))

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
        return redirect(url_for("local.local_dashboard_settings"))

    @local_bp.route("/local/plex/delete", methods=["POST"])
    def local_plex_delete():
        if not session.get("local_authenticated"):
            flash("Non autorisé.", "error")
            return redirect(url_for("local.local_login"))

        path_name = (request.form.get("path") or "").strip()
        if not path_name:
            flash("Path manquant.", "error")
            return redirect(url_for("local.local_dashboard_settings"))

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

        return redirect(url_for("local.local_dashboard_settings"))
