"""
Module Flask - Applications API et locale séparées
"""
from app.flask.manager import create_api_app, create_local_app, FlaskServer

__all__ = ["create_api_app", "create_local_app", "FlaskServer"]
