# Start from an official Python image
FROM python:3.9-slim-bookworm

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

ENV DATA=/mnt/user/appdata/anime-downloader
ENV TEMP=/tmp/anime-downloader
ENV PLEX=/mnt/user/appdata/plex

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Vérifier le contenu du fichier anime.json
RUN echo "=== Contenu de anime.json ===" && \
    cat /mnt/user/appdata/anime-downloader/config/anime.json || echo "Fichier non trouvé"

CMD ["python", "app.py"]
