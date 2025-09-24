from config import Config
import requests
from utils import CacheManager

cache = CacheManager.load_cache()

class DofusAPI:

    @staticmethod
    def get_all_equipments():
        url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/equipment"
        
        # Paramètres initiaux
        params = {
            'sort[{}'.format(Config.SORT_BY): Config.SORT_ORDER,
            'filter[min_level]': Config.MIN_LEVEL,
            'filter[max_level]': Config.MAX_LEVEL,
            'fields[item]': ','.join(Config.FIELDS),
            'filter[type.name_id]': ','.join(Config.ITEM_TYPES),
            'page[size]': -1
        }
        
        try:
            response = requests.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                # Filtrer uniquement les équipements avec une recette
                unfiltered = data.get('items', [])
                equipments = [stuff for stuff in unfiltered if 'recipe' in stuff.keys()]
                print(f"✅ {len(equipments)} équipements récupérés avec succès")
                return equipments
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de connexion: {str(e)}")
            return []
        
    @staticmethod
    def get_resource_info(resource_id):
        """Get resource info from cache or API with caching"""
        # Check cache first
        if str(resource_id) in cache:
            return cache[str(resource_id)]
        
        # If not in cache, make API request
        url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/resources/{resource_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Update cache
            cache[str(resource_id)] = data
            return data
        return None
    
    @staticmethod
    def get_resource_name(resource_id):
        """Get resource name from cache or API with caching"""
        # Check cache first
        if str(resource_id) in cache:
            return cache[str(resource_id)]
        
        # If not in cache, make API request
        url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/resources/{resource_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            name = data.get('name', f"Ressource inconnue ({resource_id})")
            # Update cache
            cache[str(resource_id)] = name
            return name
        return f"Ressource inconnue ({resource_id})"
