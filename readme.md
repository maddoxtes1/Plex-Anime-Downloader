# Description 
J'ai un serveur Plex et j'aime les animes. J'avais la flemme de downloader manuellement mes animes, du coup j'ai créé cette app Docker.

## Mes idées pour le projet

- ✅ Téléchargez automatiquement les animes.
- ✅ controller app avec une extention web.
- ❌ Pouvoir télécharger sur plusieurs sites de streaming. (pour le moment, il marche seulement avec [https://anime-sama.org/]) 
- ❌ support d'un vpn pour les download.


# Requirement 

- docker

⚠️ si tu a une bibliotheque jellyfin tu vas surment avoir des probleme avec la detection des anime 

jai fait un petit docker qui peut run h24 qui permet de cree automatiquement le nfo se qui rend la detection des anime/episode plus simple ses pas parfait mais sa aide beaucoup [lien-nfo-watcher](https://hub.docker.com/repository/docker/maddoxtes/jellyfin-nfo-watcher/general)



# Installation 

- 1 docker pull maddoxtes/plex-anime-downloader:tagname

- 2 Voici les variable que le docker app utilise.
    - DATA=/mnt/user/appdata/anime-downloader | 
    - PLEX=/mnt/user/appdata/plex | ⚠️ Ce chemin doit être votre bibliothèque de films ou séries de plex/jellyfin.
    - LOCAL_ADMIN_PASSWORD=change-moi | ses le mot de passe pour changer la confiuguration de app via un interface web 
    - 5000:5000 | api port tu ouvrir se port pour que tes amis puisse ajoute des anime a ton server plex/jellyfin
    - 5001:5001 | localdashbord port je te conseille de ne pas ouvrire se port au public

- 3 vas sur http://localhost:5000 pour configurer le server 

- 4 telecharge lextention via le localdashbord et ajoute le a ton navigateur 

- 5 quand tu est connecter a ton server avec lextention vas sur https://anime-sama.org pour download des anime 



# Tutorial

[comment installer et download des anime avec la beta-0.6.1](https://youtu.be/dXu000JrCRc)

Si vous rencontrez des problèmes avec mon application Docker ou si vous trouvez des bugs, rendez-vous sur le serveur Discord et je vous répondrai plus rapidement.



# Lien

- [Github](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Gitea](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/plex-anime-downloader)
- [Patch-note](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader/releases)
- [Discord](https://discord.gg/UG9A6MP8rE)