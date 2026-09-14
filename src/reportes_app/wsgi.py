"""Punto de entrada WSGI para gunicorn: gunicorn reportes_app.wsgi:app"""
from reportes_app import create_app

app = create_app()
