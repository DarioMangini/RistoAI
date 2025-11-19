# services/config.py
"""
Configurazione centrale dell'app:
• Parametri DB
• URI per SQLAlchemy
• Log level
• Accesso credenziali per psycopg2
"""

class Config:
    # Parametri database
    DB_NAME = "ristosushi_it"
    DB_USER = "postgres"
    DB_PASS = "Rae4ethae2qu"
    DB_HOST = "localhost"          # oppure "matrix.glacom.com"
    DB_PORT = 5432

    # URI compatibile con SQLAlchemy
    SQLALCHEMY_DATABASE_URI = (
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
