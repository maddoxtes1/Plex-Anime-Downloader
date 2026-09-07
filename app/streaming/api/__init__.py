from .anime_sama import get_panning, get_anime_details, get_episode_js, get_anime_episodes_url

# Alias pour compatibilité avec le code existant
# Utilisation de staticmethod pour que les fonctions ne reçoivent pas 'self' en argument
class anime_sama_api:
    get_panning = staticmethod(get_panning)
    get_anime_details = staticmethod(get_anime_details)
    get_episode_js = staticmethod(get_episode_js)
    get_anime_episodes_url = get_anime_episodes_url  # Classe, pas besoin de staticmethod

from .franime import get_panning, get_anime_details, get_anime_episodes_url

class franime_api:
    get_panning = staticmethod(get_panning)
    get_anime_details = staticmethod(get_anime_details) 
    get_anime_episodes_url = staticmethod(get_anime_episodes_url)