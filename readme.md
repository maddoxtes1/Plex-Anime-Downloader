# Description 
J'ai un serveur Plex et j'aime les animes. J'avais la flemme de downloader manuellement mes animes, du coup j'ai créé cette app Docker.

## Mes idées pour le projet

- ✅ Téléchargez automatiquement les animes.
- ❌ Avoir une interface web pour le contrôler.
- ❌ Utiliser une extension pour ajouter des téléchargements dans la queue.
- 🔨 Pouvoir télécharger sur plusieurs sites de streaming. (pour le moment, il marche seulement avec [https://anime-sama.fr/]) 
- ❌ Utilisation d'un VPN pour les download. (ne sera pas obligatoire, mais recommandé, sinon tu vas toujour te faire ban de sibnet)


# Requirement 

- docker


# Installation 

Voici les path que le docker app utilise.

- DATA - /mnt/user/appdata/anime-downloader ⚠️ Tu peux le mettre ou que tu veux, mais rappelle-toi ou que tu la mis parceque tu pouras pas download des anime.
- PLEX - /mnt/user/appdata/plex ⚠️ Ce chemin doit être votre bibliothèque de films ou séries de plex.

#### Après avoir pull le docker va dans (/DATA/config/). 
Si tu ne modifie pas les 3 fichier present dans /DATA/config/ le script ne marchera pas.


# Utilisation 

- 1 va sur https://anime-sama.fr/ et cherche un anime que tu aimerais download 
- 2 regarde url elle dois ressembler a sa https://anime-sama.fr/catalogue/tis-time-for-torture-princess/saison1/vostfr/
- 3 Après, tu vas dans le fichier (/DATA/config/anime.json) si c'est un anime qui se trouvait dans le planning d'anime-sama souvient toi du jour et ajoute cette ligne a série {"name": "nom-de-lanime-présent-dans-url", "season": "1", "langage": "vostfr"}, sinon recherche le jour nommé "download_all" et ajoute le dedans


# Lien

- [Github](https://github.com/maddoxtes1/Plex-Anime-Downloader)
- [Gitea](https://git.maddoxserv.com/maddox/Plex-Anime-Downloader)
- [Docker Hub](https://hub.docker.com/r/maddoxtes/plex-anime-downloader)