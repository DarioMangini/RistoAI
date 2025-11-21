# services/config.py
"""
Configurazione centrale dell'app.
I parametri sensibili sono gestiti tramite variabili d'ambiente:
• DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
• DATABASE_URL (se presente, sovrascrive gli altri parametri)
"""

import os

class Config:
    # Parametri database
    DB_NAME = os.getenv("DB_NAME", "demo_restaurant")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "postgres")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))

    # URI compatibile con SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Livello di logging globale
    LOG_LEVEL = "DEBUG"


    # ▶︎  Dict comodo per psycopg2
    @classmethod
    def pg_dict(cls) -> dict:
        """
        Restituisce un dizionario con le credenziali per psycopg2.
        """
        return dict(
            dbname   = cls.DB_NAME,
            user     = cls.DB_USER,
            password = cls.DB_PASS,
            host     = cls.DB_HOST,
            port     = cls.DB_PORT,
        )
