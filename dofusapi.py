from config import Config
import requests

class DofusAPI:
    @staticmethod
    def get_all_equipments():
        all_equipments = []
        page_number = 1
        total_pages = 1

        while True:
            base_url = f"https://api.dofusdu.de/{Config.GAME}/v1/{Config.LANGUAGE}/items/equipment"
            params = {
                'sort[{}'.format(Config.SORT_BY): Config.SORT_ORDER,
                'filter[min_level]': Config.MIN_LEVEL,
                'filter[max_level]': Config.MAX_LEVEL,
                'fields[item]': ','.join(Config.FIELDS),
                'filter[type.name_id]': ','.join(Config.ITEM_TYPES),
                'page[size]': Config.PAGE_SIZE,
                'page[number]': page_number
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                equipments = data.get('items', [])
                all_equipments.extend(equipments)

                if 'meta' in data and 'last_page' in data['meta']:
                    total_pages = data['meta']['last_page']

                print(f"Page {page_number}/{total_pages} - {len(equipments)} équipements récupérés")

                if page_number >= total_pages or not equipments:
                    break

                page_number += 1
            else:
                print(f"Erreur lors de la requête : {response.status_code}")
                break

        return all_equipments

    @staticmethod
    def get_resource_name(resource_id, cache):
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
