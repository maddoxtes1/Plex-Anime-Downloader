import requests 
from bs4 import BeautifulSoup
import logging
import re

def sibnet_scrap(url):
    logger = logging.getLogger("Sibnet Scraper")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive", "Upgrade-Insecure-Requests": "1"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        scripts = soup.find_all('script', type="text/javascript")
        
        if not scripts:
            logger.error("Aucun script JavaScript trouvé dans la page")
            return None
            
        for script in scripts:
            script_content = script.string
            if script_content:
                match = re.search(r'player\.src\(\[\{src: "(.*?)"', script_content)
                if match:
                    video_url = match.group(1)
                    if not video_url:
                        logger.error("URL de la vidéo non trouvée dans le script")
                        return None
                    mp4_url = f"https://video.sibnet.ru{video_url}"
                    return mp4_url
                    
        logger.error("Aucune URL de vidéo trouvée dans les scripts")
        return None
        
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête HTTP: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return None

def vidmoly_scrap(url, segmentation_path):
    logger = logging.getLogger("Vidmoly Scraper")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',"Referer": "https://vidmoly.to/"}

    def make_request(url, error_message):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"{error_message}: {e}")
            return None

    # Première étape : Récupérer l'URL m3u8
    response = make_request(url, "Erreur lors de la récupération de l'URL m3u8")
    if not response:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    m3u8_url = None
    for script in soup.find_all('script'):
        if script.string:
            match = re.search(r'(https?://[^\s]+/master\.m3u8)', script.string)
            if match:
                m3u8_url = match.group(1)
                break

    if not m3u8_url:
        logger.error("URL m3u8 non trouvée")
        return None

    # Deuxième étape : Récupérer la meilleure qualité
    response = make_request(m3u8_url, "Erreur lors de la récupération de la meilleure qualité")
    if not response:
        return None

    lines = response.text.splitlines()
    best_url = None
    best_resolution = (0, 0)

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            resolution_str = next((part.split("=")[1] for part in line.split(",") 
                                 if part.startswith("RESOLUTION=")), None)
            if resolution_str and i + 1 < len(lines):
                width, height = map(int, resolution_str.split("x"))
                if (width, height) > best_resolution:
                    best_resolution = (width, height)
                    best_url = lines[i + 1]

    if not best_url:
        logger.error("Meilleure qualité non trouvée")
        return None

    # Troisième étape : Récupérer les segments
    response = make_request(best_url, "Erreur lors de la récupération des segments")
    if not response:
        return None

    segment_urls = [line for line in response.text.splitlines() 
                   if line and not line.startswith('#')]

    if not segment_urls:
        logger.error("Aucun segment trouvé")
        return None

    return [(url, f"{segmentation_path}seg-{i+1}.ts") 
            for i, url in enumerate(segment_urls)]

def oneupload_scrap(url, segmentation_path):
    logger = logging.getLogger("Oneupload Scraper")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        "Referer": "https://oneupload.net/"
    }

    def make_request(url, error_message):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"{error_message}: {e}")
            return None

    # Première étape : Récupérer l'URL m3u8
    response = make_request(url, "Erreur lors de la récupération de l'URL m3u8")
    if not response:
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    m3u8_url = None
    for script in soup.find_all('script'):
        if script.string:
            match = re.search(r'file:"(https?://[^"]+\.m3u8[^"]*)"', script.string)
            if match:
                m3u8_url = match.group(1)
                break

    if not m3u8_url:
        logger.error("URL m3u8 non trouvée")
        return None

    # Deuxième étape : Récupérer la meilleure qualité
    response = make_request(m3u8_url, "Erreur lors de la récupération de la meilleure qualité")
    if not response:
        return None

    lines = response.text.splitlines()
    best_url = None
    best_resolution = (0, 0)

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            resolution_str = next((part.split("=")[1] for part in line.split(",") 
                                 if part.startswith("RESOLUTION=")), None)
            if resolution_str and i + 1 < len(lines):
                width, height = map(int, resolution_str.split("x"))
                if (width, height) > best_resolution:
                    best_resolution = (width, height)
                    best_url = lines[i + 1]

    if not best_url:
        logger.error("Meilleure qualité non trouvée")
        return None

    # Troisième étape : Récupérer les segments
    response = make_request(best_url, "Erreur lors de la récupération des segments")
    if not response:
        return None

    segment_urls = [line for line in response.text.splitlines() 
                   if line and not line.startswith('#')]

    if not segment_urls:
        logger.error("Aucun segment trouvé")
        return None

    return [(url, f"{segmentation_path}seg-{i+1}.ts") 
            for i, url in enumerate(segment_urls)]

def sendvid_scrap(url):
    logger = logging.getLogger("Sendvid Scraper")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, br", "Connection": "keep-alive", "Upgrade-Insecure-Requests": "1"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        meta_tag = soup.find("meta", property="og:video")
        
        if not meta_tag:
            logger.error("Aucune vidéo trouvée dans la page")
            return None
            
        mp4_url = meta_tag['content']
        if not mp4_url:
            logger.error("URL de la vidéo non trouvée")
            return None
            
        return mp4_url
        
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la requête HTTP: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return None

