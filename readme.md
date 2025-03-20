# Description 
J'ai un serveur Plex et j'aime les animes. J'avais la flemme de downloader manuellement mes animes, du coup j'ai créé cette app Docker.

## Mes idées pour le projet

- ✅ Téléchargez automatiquement les animes.
- 🔨 Avoir une interface web pour le contrôler.
- ❌ Utiliser une extension pour ajouter des téléchargements dans la queue.
- ❌ Pouvoir télécharger sur plusieurs sites de streaming. (pour le moment, il marche seulement avec [https://anime-sama.fr/]) 
- ❌ Utilisation d'un VPN pour les download. (ne sera pas obligatoire, mais recommandé, sinon tu vas toujour te faire ban de sibnet)


# Requirement 

- docker


# Installation 

Voici les 3 path que le docker app utilise.

- DATA - /mnt/user/appdata/anime-downloader ⚠️
- TEMP - /tmp/anime-downloader ✅
- PLEX - /mnt/user/appdata/plex ⚠️

#### Les path ✅ tu a pas besoin de les changer, mais celles avec ⚠️ tu vas devoir les changer 

- DATA Tu peux le mettre ou que tu veux, mais rappelle-toi ou que tu la mis parceque tu pouras pas download des anime.
- PLEX Ce chemin doit être votre bibliothèque de films et de séries.

#### Après avoir pull le docker va dans (/DATA/config/config.conf), Pour changer le nom des dossier "vostfr_folder_name" et "vf_folder_name". 
Le nom des 2 dossier dois être présent dans le path PLEX.

# Utilisation 

- 1 va sur https://anime-sama.fr/ et cherche un anime que tu aimerais download 
- 2 regarde url elle dois ressembler a sa https://anime-sama.fr/catalogue/tis-time-for-torture-princess/saison1/vostfr/
- 3 Après, tu vas dans le fichier (/DATA/config/anime.json) si c'est un anime qui se trouvait dans le planning d'anime-sama souvient toi du jour et ajoute cette ligne a série {"name": "nom-de-lanime-présent-dans-url", "season": "1", "langage": "vostfr"}, sinon recherche le jour nommé "download_all" et ajoute le dedans


# Lien

- [Github](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Gitea](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/anime-sama_downloader)