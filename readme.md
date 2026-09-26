# Plex Anime Downloader

Plex Anime Downloader est une petite application permettant de télécharger facilement des animes et de les organiser dans une bibliothèque Plex, Jellyfin ou Emby.

J'utilise personnellement un serveur Plex/Jellyfin/Emby et j'aime beaucoup les animes. Je trouvais que mettre en place une solution complète avec Sonarr + qBittorrent était un peu compliqué pour quelque chose d'aussi simple.

J'ai donc créé ce projet avec une interface web permettant de rechercher et télécharger des animes plus facilement.

## ✨ Fonctionnalités

- ✅ Téléchargement automatique des animes
- ✅ Téléchargement depuis plusieurs sites de streaming
  - Anime-Sama
  - Franime
- ✅ Interface web pour gérer les téléchargements
- ✅ Organisation des fichiers pour Plex/Emby

## 📺 Compatibilité

L'application peut être utilisée avec :

- 🟢 Plex
- 🟢 Emby
- 🟡 Jellyfin

> ⚠️ **Jellyfin :** vous pouvez rencontrer des problèmes avec la détection des animes et des épisodes selon la structure de votre bibliothèque.

## 📋 Prérequis

- Docker
- Docker Compose

> 💡 Une bibliothèque Plex, Emby ou Jellyfin **n'est pas obligatoire**. Elle est uniquement nécessaire si vous souhaitez organiser automatiquement les fichiers téléchargés dans votre bibliothèque multimédia.

## 🚀 Installation

### Méthode rapide avec Docker Compose

Créez un fichier `docker-compose.yml` avec le contenu suivant :

```yaml
services:
  anime-sama_downloader:
    image: maddoxtes/plex-anime-downloader:beta-0.9.0

    volumes:
      - /chemin/vers/vos/donnees:/mnt/user/appdata/anime-downloader
      - /chemin/vers/votre/bibliotheque/plex:/mnt/user/appdata/plex

    environment:
      - LOCAL_ADMIN_PASSWORD=votre_mot_de_passe_securise

    ports:
      - "5000:5000"
```

### 📁 Volumes

#### Données de l'application

```yaml
- /chemin/vers/vos/donnees:/mnt/user/appdata/anime-downloader
```

Ce dossier contient les données et la configuration de l'application.

#### Bibliothèque multimédia

```yaml
- /chemin/vers/votre/bibliotheque/plex:/mnt/user/appdata/plex
```

Si vous utilisez une bibliothèque multimédia, ce chemin doit correspondre à l'emplacement multimédia de votre plex/emby/jellyfin.

> ⚠️ Assurez-vous que le conteneur Docker possède les permissions nécessaires pour lire et écrire dans ce dossier.

## 🔐 Variables d'environnement

| Variable | Description |
|----------|-------------|
| `LOCAL_ADMIN_PASSWORD` | Mot de passe permettant d'accéder au dashboard et de modifier la configuration |
| `DATA` | Chemin des données de l'application |
| `PLEX` | Chemin de la bibliothèque multimédia |

> 💡 Les variables `DATA` et `PLEX` dépendent de votre configuration. Les chemins utilisés dans le conteneur doivent correspondre aux volumes définis dans votre `docker-compose.yml`.

## 🌐 Port

Le dashboard est accessible sur :

```text
http://localhost:5000
```

> ⚠️ **Sécurité :** ne rendez pas ce port accessible depuis Internet.

## ▶️ Démarrer l'application

### Télécharger l'image Docker

```bash
docker compose pull
```

### Démarrer le conteneur

```bash
docker compose up -d
```

### Voir les logs

```bash
docker compose logs -f
```

### Arrêter l'application

```bash
docker compose down
```

## ⚙️ Configuration

Une fois le conteneur démarré, ouvrez :

```text
http://localhost:5000
```

Connectez-vous avec le mot de passe défini dans :

```yaml
LOCAL_ADMIN_PASSWORD
```

Vous pourrez ensuite configurer l'application depuis l'interface web.

## 📖 Tutoriel

[Comment installer et télécharger des animes avec la version beta-0.9.0]()

## 🐛 Problèmes et bugs

Si vous rencontrez un problème avec l'application Docker ou si vous trouvez un bug, merci de créer une **issue sur GitHub**.

## 🔗 Liens

- [GitHub](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/plex-anime-downloader)
- [Patch notes](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader/releases)
