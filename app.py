# app.py

# Importa la funzione create_app che crea e configura l'app Flask
from factory.app_factory import create_app

import logging

# Crea un'istanza dell'applicazione Flask utilizzando la factory
app = create_app()

# Avvia l'applicazione
if __name__ == "__main__":
    # Stampa di debug per verificare l'avvio dell'applicazione
    logging.debug("[app.py] Avvio dell'applicazione Flask")
    
    # Avvia il server Flask sull'host 0.0.0.0 (accessibile da tutte le interfacce di rete)
    # Porta configurata su 5010 
    app.run(host="0.0.0.0", port=5010)
