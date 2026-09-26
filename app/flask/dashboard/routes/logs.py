"""
Routes pour la page Logs (logs.html)
"""
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    Response,
    stream_with_context,
)
import os
import json
import time
from app.flask.dashboard.routes.common import prepare_dashboard_data
from app.sys import FolderConfig


def register_logs_routes(local_bp, helpers, plex_root, config_path):
    """
    Enregistre les routes pour la page Logs.
    
    Args:
        local_bp: Blueprint Flask
        helpers: Instance de FlaskHelpers
        plex_root: Chemin racine Plex
        config_path: Chemin vers le dossier de configuration
    """
    
    @local_bp.route("/logs")
    def local_dashboard_logs():
        """Page Logs"""
        if not session.get("local_authenticated"):
            flash("Vous devez être connecté avec le mot de passe admin.", "error")
            return redirect(url_for("local.local_login"))
        
        data = prepare_dashboard_data(helpers, plex_root, config_path)
        return render_template("logs.html", **data)

    @local_bp.route("/local/logs/list", methods=["GET"])
    def local_logs_list():
        """Retourne la liste des fichiers de logs"""
        if not session.get("local_authenticated"):
            return jsonify({"ok": False, "error": "Non autorisé"}), 401
        
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

    def local_logs_stream_docker():
        """Stream les logs de l'application en temps réel (tous les fichiers de logs combinés)"""
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

    @local_bp.route("/local/logs/stream/<filename>", methods=["GET"])
    def local_logs_stream(filename):
        """Stream les logs en temps réel (Server-Sent Events)"""
        if not session.get("local_authenticated"):
            return jsonify({"ok": False, "error": "Non autorisé"}), 401
        
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

