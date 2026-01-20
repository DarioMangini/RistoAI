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

# 1. Aggiorna pip per sicurezza
RUN pip install --upgrade pip

# 2. Installa PRIMA la versione CPU di PyTorch (molto più leggera)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 3. Ora installa il resto (che troverà torch già installato e non scaricherà quello gigante)
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice nel container
COPY . .

# Espone la porta configurata in app.py
EXPOSE 5010

# Comando per avviare l'app
CMD ["python", "app.py"]