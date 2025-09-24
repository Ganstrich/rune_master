import requests
from collections import defaultdict
import json
import os

# Cache configuration
CACHE_FILE = 'resource_cache.json'

def load_cache():
    """Load resource names from cache file if it exists"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_cache(cache):
    """Save resource names to cache file"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

# Load existing cache
resource_cache = load_cache()

# Paramètres de la requête
language = 'fr'
game = 'dofus3'
sort_by = 'level'
sort_order = 'desc'
min_level = 50
max_level = 100
item_types = []
fields = ['recipe']
min_common_items = 3
page_size = 100

# Fonction pour récupérer tous les équipements
def get_all_equipments():
    all_equipments = []
    page_number = 1
    total_pages = 1

    while True:
        base_url = f"https://api.dofusdu.de/{game}/v1/{language}/items/equipment"
        params = {
            'sort[{}'.format(sort_by): sort_order,
            'filter[min_level]': min_level,
            'filter[max_level]': max_level,
            'fields[item]': ','.join(fields),
            'filter[type.name_id]': ','.join(item_types),
            'page[size]': page_size,
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

# Get resource names with caching
def get_resource_name(resource_id):
    """Get resource name from cache or API with caching"""
    # Check cache first
    if str(resource_id) in resource_cache:
        return resource_cache[str(resource_id)]
    
    # If not in cache, make API request
    url = f"https://api.dofusdu.de/{game}/v1/{language}/items/resources/{resource_id}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        name = data.get('name', f"Ressource inconnue ({resource_id})")
        # Update cache
        resource_cache[str(resource_id)] = name
        return name
    return f"Ressource inconnue ({resource_id})"

# Récupérer tous les équipements
equipments = get_all_equipments()
print(f"\nTotal d'équipements récupérés: {len(equipments)}")

if equipments:
    # Extraire les IDs des objets pour chaque recette
    recipe_ids = []
    equipment_names = []
    equipment_recipes = []
    unique_resource_ids = set()

    # D'abord, collecter tous les IDs de ressources uniques
    for equipment in equipments:
        equipment_names.append(equipment["name"])
        recipe = equipment.get("recipe", [])
        ids = [item["item_ankama_id"] for item in recipe]
        recipe_ids.append(ids)
        equipment_recipes.append(recipe)
        for item in recipe:
            if item["item_subtype"] == "resources":
                unique_resource_ids.add(item["item_ankama_id"])

    # Créer un cache pour les noms de ressources
    resource_names = {}
    print(f"\nRécupération des noms pour {len(unique_resource_ids)} ressources uniques...")
    for resource_id in unique_resource_ids:
        resource_names[resource_id] = get_resource_name(resource_id)
        print(f"Ressource {resource_id}: {resource_names[resource_id]}")
        
    # Save the cache after fetching all resource names
    save_cache(resource_cache)

    # Créer un graphe de connexion entre équipements
    graph = defaultdict(list)
    for i in range(len(equipments)):
        for j in range(i + 1, len(equipments)):
            common = set(recipe_ids[i]) & set(recipe_ids[j])
            if len(common) >= min_common_items:
                graph[equipment_names[i]].append(equipment_names[j])
                graph[equipment_names[j]].append(equipment_names[i])

    # Fonction pour trouver les clusters connectés
    def find_clusters():
        clusters = []
        visited = set()

        def dfs(node, cluster):
            if node not in visited:
                visited.add(node)
                cluster.append(node)
                for neighbor in graph.get(node, []):
                    dfs(neighbor, cluster)

        for name in equipment_names:
            if name not in visited:
                cluster = []
                dfs(name, cluster)
                if len(cluster) > 1:
                    clusters.append(cluster)
        return clusters

    clusters = find_clusters()

    # Afficher les résultats avec les ingrédients totaux
    if clusters:
        print(f"\nGroupes d'équipements partageant au moins {min_common_items} objets communs :")
        for i, cluster in enumerate(clusters, 1):
            print(f"\nGroupe {i} ({len(cluster)} équipements):")

            # Calculer les ingrédients totaux pour ce groupe
            ingredients = defaultdict(int)
            for equipment_name in cluster:
                index = equipment_names.index(equipment_name)
                for item in equipment_recipes[index]:
                    if item["item_subtype"] == "resources":
                        ingredients[item["item_ankama_id"]] += item["quantity"]

            print("Équipements du groupe:")
            for name in cluster:
                print(f"- {name}")

            print("\nIngrédients nécessaires pour crafter le groupe entier:")
            for item_id, quantity in sorted(ingredients.items()):
                print(f"- {resource_names.get(item_id, f'Ressource {item_id}')}: {quantity} unités")

            print("-" * 50)
    else:
        print(f"\nAucun groupe ne partage au moins {min_common_items} objets communs.")