# Utiliser une image de base Python officielle légère
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les outils systèmes requis
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code source
COPY . .

# S'assurer que le dossier data/ existe pour la base de données
RUN mkdir -p data

# Exposer le port par défaut configuré (8080)
EXPOSE 8080

# Commande de démarrage de Streamlit
ENTRYPOINT ["streamlit", "run", "app.py"]
