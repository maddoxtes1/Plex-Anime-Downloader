
I broke all the old push ;(

not finished yet, I am working on a web interface to facilitate downloading

git - https://git.maddoxserv.com/maddox/DOCKER-APP_plex-anime-downloader⁠

docker - maddoxtes/anime-sama_downloader

need 3 path

DATA=/mnt/user/appdata/anime-downloader

TEMP=/tmp/anime-downloader

PLEX=/mnt/user/appdata/plex

and to be able to download an anime go on https://anime-sama.fr/planning/⁠ select your anime and you must write this in the anime.json

exemple for this anime https://anime-sama.fr/catalogue/izure-saikyou-no-renkinjutsushi/saison1/vostfr/⁠ {"day": "mercredi","series": [{"name": "izure-saikyou-no-renkinjutsushi","season": "1","langage": "vostfr"}]},

If you are using beta-0.4.3 and want to update to 0.4.5 you will have to delete your anime.json file. I advise you to backup your old file to copy it into the new one.

for each anime and anime season