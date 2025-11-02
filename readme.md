# Description 
J'ai un serveur Plex et j'aime les animes. J'avais la flemme de downloader manuellement mes animes, du coup j'ai créé cette app Docker.

## Mes idées pour le projet

- ✅ Téléchargez automatiquement les animes.
- 🔨 controller app avec une extention web.
- ❌ Pouvoir télécharger sur plusieurs sites de streaming. (pour le moment, il marche seulement avec [https://anime-sama.org/]) 
- ❌ support d'un vpn pour les download.


# Requirement 

- docker

⚠️ si tu a une bibliotheque jellyfin tu vas surment avoir des probleme avec la detection des anime 

jai fait un petit docker qui peut run h24 qui permet de cree automatiquement le nfo se qui rend la detection des anime/episode plus simple ses pas parfait mais sa aide beaucoup [lien-nfo-watcher](https://hub.docker.com/repository/docker/maddoxtes/jellyfin-nfo-watcher/general)



# Installation 

- 1 docker pull maddoxtes/plex-anime-downloader:tagname

- 2 Voici les path que le docker app utilise.
    - DATA - /mnt/user/appdata/anime-downloader ⚠️ Tu peux le mettre ou que tu veux, mais rappelle-toi ou que tu la mis parceque tu pouras pas download des anime.
    - PLEX - /mnt/user/appdata/plex ⚠️ Ce chemin doit être votre bibliothèque de films ou séries de plex.

- 3 modifie le fichier plex_path.json il est present dans /DATA/config/ sinon le script ne marchera pas.

- 4 modifie le fichier anime.json pour ajouter des anime dans ta bibliotech plex/jellyfin/offline download 



# Tutorial

[comment download des anime](https://youtu.be/5oiUDOtd_ww)



# Lien

- [Github](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Gitea](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/plex-anime-downloader)
- [Patch-note](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader/releases)