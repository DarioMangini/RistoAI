# core/db.py
"""
Inizializza SQLAlchemy e crea le tabelle dell'applicazione.
Include il supporto a pgvector (embedding vettoriali).
"""
from flask_sqlalchemy import SQLAlchemy

# Oggetto globale SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    """
    Collega l'app Flask a SQLAlchemy e crea le tabelle definite in models.
    """
    db.init_app(app)
    with app.app_context():
        from core import models  
        db.create_all()
