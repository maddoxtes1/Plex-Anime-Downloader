# Description 

J'ai un serveur Plex et j'aime les animes. J'avais la flemme de télécharger manuellement mes animes, du coup j'ai créé cette application Docker.

## Fonctionnalités du projet

- ✅ Télécharger automatiquement les animes
- ✅ Contrôler l'application avec une extension web
- ❌ Télécharger depuis plusieurs sites de streaming (pour le moment, cela fonctionne uniquement avec [https://anime-sama.org/])
- ❌ Support d'un VPN pour les téléchargements

## Prérequis

- Docker installé sur votre système

⚠️ **Note importante** : Si vous avez une bibliothèque Jellyfin, vous allez probablement rencontrer des problèmes avec la détection des animes.

J'ai créé un petit conteneur Docker qui peut tourner 24/7 et qui permet de créer automatiquement les fichiers NFO, ce qui facilite la détection des animes/épisodes. Ce n'est pas parfait mais cela aide beaucoup : [lien-nfo-watcher](https://hub.docker.com/repository/docker/maddoxtes/jellyfin-nfo-watcher/general)

# Installation

## Méthode rapide avec Docker Compose

### 1. Créer un fichier docker-compose.yml

Créez un fichier `docker-compose.yml` avec le contenu suivant :

```yaml
services:
  anime-sama_downloader:
    image: maddoxtes/plex-anime-downloader:beta-0.6.1
    volumes:
      - /chemin/vers/vos/donnees:/mnt/user/appdata/anime-downloader
      - /chemin/vers/votre/bibliotheque/plex:/mnt/user/appdata/plex
    environment:
      - LOCAL_ADMIN_PASSWORD=votre_mot_de_passe_securise
    ports:
      - 5000:5000  # API (public, pour reverse proxy)
      - 5001:5001  # Dashboard local (ne PAS exposer au public)
```

### 2. Variables d'environnement importantes

- **DATA** : Chemin vers les données de l'application (par défaut : `/mnt/user/appdata/anime-downloader`)
- **PLEX** : Chemin vers votre bibliothèque Plex/Jellyfin (⚠️ Ce chemin doit être votre bibliothèque de films ou séries)
- **LOCAL_ADMIN_PASSWORD** : Mot de passe pour accéder au dashboard local et modifier la configuration via l'interface web
- **FLASK_SECRET_KEY** : Clé secrète pour les sessions Flask (générez une clé aléatoire)
- **USE_WAITRESS** : `true` pour utiliser Waitress (production) ou `false` pour le serveur de développement

### 3. Ports

- **5000:5000** : Port de l'API - Ouvrez ce port pour que vos amis puissent ajouter des animes à votre serveur Plex/Jellyfin
- **5001:5001** : Port du dashboard local - ⚠️ Je vous conseille de ne PAS ouvrir ce port au public pour des raisons de sécurité

### 4. Démarrer l'application

```bash
# Télécharger l'image
docker-compose pull

# Démarrer le conteneur
docker-compose up -d

# Voir les logs
docker-compose logs -f
```

### 5. Configuration

1. Accédez à http://localhost:5001 pour configurer le serveur
2. Connectez-vous avec le mot de passe défini dans `LOCAL_ADMIN_PASSWORD`
3. Téléchargez l'extension via le dashboard local et ajoutez-la à votre navigateur
4. Une fois connecté à votre serveur avec l'extension, allez sur https://anime-sama.org pour télécharger des animes 



# Tutoriel

[Comment installer et télécharger des animes avec la beta-0.6.1](https://youtu.be/dXu000JrCRc)

Si vous rencontrez des problèmes avec mon application Docker ou si vous trouvez des bugs, rendez-vous sur le serveur Discord et je vous répondrai plus rapidement.



# Lien

- [Github](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Gitea](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/plex-anime-downloader)
- [Patch-note](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader/releases)
- [Discord](https://discord.gg/UG9A6MP8rE)