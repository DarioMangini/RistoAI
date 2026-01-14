# Usa un'immagine Python leggera
FROM python:3.10-slim

# Imposta la cartella di lavoro nel container
WORKDIR /app

# Installa le dipendenze di sistema necessarie per psycopg2 e modelli AI
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e installa i requisiti Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice nel container
COPY . .

# Espone la porta configurata in app.py
EXPOSE 5010

# Comando per avviare l'app
CMD ["python", "app.py"]