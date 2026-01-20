# core/models.py
"""
Definisce i modelli SQLAlchemy dell'app:
• Menu       – piatti disponibili
• Recensioni – recensioni testuali dei clienti

Entrambe le tabelle contengono un embedding SBERT (pgvector).
"""

from core.db import db                 
from pgvector.sqlalchemy import Vector

VECTOR_DIM = 1536

class Menu(db.Model):
    __tablename__ = "menu"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.Text, nullable=False)
    type        = db.Column(db.Text)
    ingredients = db.Column(db.ARRAY(db.Text))
    description = db.Column(db.Text)
    embedding   = db.Column(Vector(VECTOR_DIM))       # pgvector
    price       = db.Column(db.Numeric(10, 2))

class Recensioni(db.Model):
    __tablename__ = "recensioni"

    id         = db.Column(db.Uuid, primary_key=True)
    voto       = db.Column(db.Integer, nullable=False)
    recensione = db.Column(db.Text,    nullable=False)
    piatti     = db.Column(db.Text)                 # JSON serializzato (str)
    embedding  = db.Column(Vector(VECTOR_DIM))