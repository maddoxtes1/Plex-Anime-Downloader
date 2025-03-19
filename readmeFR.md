# Description 
j'ai un serveur plex et j'aime les anime et j'avais la flemme de download manuelment mes anime ducoup j'ai cree ce app docker.

## Mes idee pour le project

- ✅ Download automatiquement les anime.
- 🔨 Avoir une interface web pour le controller.
- ❌ Utiliser une extention pour ajouter des telechargment dans la queue.
- ❌ Pouvoir download sur plusieur site de streaming. (pour le moment il marche seulement avec [https://anime-sama.fr/]) 
- ❌ Utilisation d'un vpn pour les download. (ne sera pas obligatoire mais recommandé sinon tu va toujour te faire ban de sibnet)


# Requirement 

- docker


# Installation 

Voci les 3 path que le docker app utilise.

- DATA - /mnt/user/appdata/anime-downloader ⚠️
- TEMP - /tmp/anime-downloader ✅
- PLEX - /mnt/user/appdata/plex ⚠️

#### les path ✅ tu a pas besoin de les changer mais eu avec ⚠️ tu va devoir les changer 

- DATA Tu peux le mettre ou que tu veux mais rappelle toi ou que tu la mis parceque tu pouras pas download des anime.
- PLEX Ce chemin doit être votre bibliothèque de films et de séries.

#### Apres avoir pull le docker va dans (/DATA/config/config.conf), Pour changer le nom des dossier "vostfr_folder_name" et "vf_folder_name". 
Le nom des 2 dossier dois etre present dans le path PLEX.

# Utilisation 

- 1 va sur https://anime-sama.fr/ et cherche un anime que tu aimerais download 
- 2 regarde url elle dois resembler a sa https://anime-sama.fr/catalogue/tis-time-for-torture-princess/saison1/vostfr/
- 3 Après, tu vas dans le fichier (/DATA/config/anime.json) si c'est un anime qui se trouvait dans le planning d'anime-sama souvient toi du jour et ajoute cette ligne a série {"name": "nom-de-lanime-présent-dans-url", "season": "1", "langage": "vostfr"}, sinon recherche le jour nommé "download_all" et ajoute le dedans


# Lien

- [Git](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Image](https://hub.docker.com/r/maddoxtes/anime-sama_downloader)