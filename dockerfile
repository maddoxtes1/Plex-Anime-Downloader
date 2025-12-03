# Start from an official Python image
FROM python:3.9-slim-bookworm

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

ENV DATA=/mnt/user/appdata/anime-downloader
ENV PLEX=/mnt/user/appdata/plex
ENV LOCAL_ADMIN_PASSWORD=change-moi-en-production
ENV SECRET_KEY=change-me-en-production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "app.py"]
