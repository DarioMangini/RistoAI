# core/db.py
"""
Inizializza SQLAlchemy e crea le tabelle dell'applicazione.
Include il supporto a pgvector (embedding vettoriali).
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Oggetto globale SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    """
    Collega l'app Flask a SQLAlchemy e crea le tabelle.
    """
    db.init_app(app)
    with app.app_context():
        try:
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.session.commit()
        except Exception as e:
            print(f"⚠️ Attenzione: Impossibile attivare estensione vector: {e}")
        # -----------------------------------------

        from core import models  
        db.create_all()
