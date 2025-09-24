import requests
import json

def get_all_equipments_complete():
    """
    Récupère la liste complète de tous les équipements sans aucun filtre
    en une seule requête en utilisant page[size]=-1
    """
    url = "https://api.dofusdu.de/dofus3/v1/fr/items/equipment"
    
    # Paramètres pour désactiver la pagination et récupérer tous les équipements
    params = {
        'page[size]': -1,  # Désactive la pagination - récupère tout en une fois
        'fields[item]': ['recipe']  # Champs à récupérer
    }
    
    print("Récupération de tous les équipements en une seule requête...")
    
    try:
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            equipments = data.get('items', [])
            print(f"✅ {len(equipments)} équipements récupérés avec succès")
            return equipments
        else:
            print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {str(e)}")
        return []

def save_equipments_to_file(equipments, filename="all_equipments_complete.json"):
    """Sauvegarde la liste complète des équipements dans un fichier JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(equipments, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(equipments)} équipements sauvegardés dans {filename}")
    return filename

# Exemple d'utilisation
if __name__ == "__main__":
    print("Début de la récupération de tous les équipements...")
    
    # Récupérer tous les équipements sans filtre en une seule requête
    all_equipments = get_all_equipments_complete()
    
    # Sauvegarder les données
    if all_equipments:
        filename = save_equipments_to_file(all_equipments)
        print(f"Données sauvegardées avec succès dans {filename}")
        
        # Afficher quelques statistiques
        print(f"\n📊 Statistiques:")
        print(f"Total d'équipements: {len(all_equipments)}")
        
        # Compter par type d'équipement
        types_count = {}
        for eq in all_equipments:
            eq_type = eq.get('type', {}).get('name', 'Inconnu')
            types_count[eq_type] = types_count.get(eq_type, 0) + 1
        
        print("\n📋 Répartition par type:")
        for eq_type, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {eq_type}: {count}")
            
    else:
        print("Aucun équipement récupéré.")