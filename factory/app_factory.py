# factory/app_factory.py

from flask import Flask
from core.config import Config                  # Configurazione centralizzata dell'app
from core.db import init_db                     # Funzione per inizializzare il database
from routes.menu import menu_bp                 # Blueprint per le rotte del menu
from routes.ingredients import ingredients_bp   # Blueprint per le rotte degli ingredienti
from routes.cart import cart_bp                 # Blueprint per le rotte del carrello
from routes.chat import chat_bp                 # Blueprint per la chat AI

import logging, sys

# Configurazione del logging globale dell'applicazione
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True, # forza la sovrascrittura di eventuali configurazioni precedenti del logging
)


def create_app() -> Flask:
    """
    Factory per creare e configurare l'app Flask.
    Utilizzata per garantire modularità e testabilità del progetto.
    """
    app = Flask(__name__)

    # Caricamento della configurazione da oggetto Config 
    app.config.from_object(Config)

    # Inizializzazione del database con l'app Flask
    init_db(app)

    # Registrazione dei Blueprint: ciascun modulo gestisce un sottoinsieme delle API REST
    app.register_blueprint(menu_bp, url_prefix="/ristosushi_it")        # Rotte per il menu
    app.register_blueprint(ingredients_bp, url_prefix="/ristosushi_it") # Rotte per gli ingredienti
    app.register_blueprint(cart_bp, url_prefix="/ristosushi_it")        # Rotte per il carrello
    app.register_blueprint(chat_bp, url_prefix="/ristosushi_it")        # Rotte per la chat AI

    return app
