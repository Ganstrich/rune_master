# ==================== CONFIGURATION ====================
from config import Config

from utils import CacheManager, ExclusionManager
# ==================== API COMMUNICATION ====================
from dofusapi import DofusAPI
# ==================== DATA PROCESSING ====================
from dataprocessor import DataProcessor
# ==================== VISUALIZATION ====================
from htmlvisualizer import HTMLVisualizer

# ==================== MAIN EXECUTION ====================
def main():
    # Charger le cache
    resource_cache = CacheManager.load_cache()
    
    # Charger les exclusions
    exclusions = ExclusionManager.load_exclusions()
    
    # Récupérer les équipements
    print("Récupération des équipements...")
    equipments = DofusAPI.get_all_equipments()
    print(f"Total d'équipements récupérés: {len(equipments)}")
    
    # Appliquer les exclusions
    equipments = ExclusionManager.filter_equipments(equipments, exclusions)
    print(f"Équipements après exclusion: {len(equipments)}")
    
    if not equipments:
        print("Aucun équipement trouvé après exclusion.")
        return
    
    # Extraire les données des équipements
    equipment_names, equipment_recipes, equipment_data, recipe_ids, unique_resource_ids = DataProcessor.extract_equipment_data(equipments)
    
    # Récupérer les noms des ressources
    print(f"Récupération des noms pour {len(unique_resource_ids)} ressources uniques...")
    resource_names = {}
    for resource_id in unique_resource_ids:
        resource_names[resource_id] = DofusAPI.get_resource_name(resource_id, resource_cache)
    
    # Sauvegarder le cache
    CacheManager.save_cache(resource_cache)
    
    # Construire le graphe de similarité avec scores
    graph, similarity_scores = DataProcessor.build_similarity_graph_with_scores(
        equipment_names, equipment_recipes, Config.MIN_SIMILARITY
    )
    
    # Trouver les clusters optimaux
    clusters = DataProcessor.find_optimal_clusters(graph, equipment_names, Config.MIN_CLUSTER_SIZE)
    
    # Évaluer la qualité de chaque cluster
    cluster_qualities = []
    for cluster in clusters:
        quality = DataProcessor.evaluate_cluster_quality(
            cluster, equipment_names, equipment_recipes, resource_names
        )
        cluster_qualities.append(quality)
    
    # Trier les clusters par score d'économie (meilleurs clusters en premier)
    if clusters and cluster_qualities:
        sorted_clusters = sorted(
            zip(clusters, cluster_qualities),
            key=lambda x: x[1]['economy_score'],
            reverse=True
        )
        clusters, cluster_qualities = zip(*sorted_clusters)
    else:
        clusters = []
        cluster_qualities = []
    
    # Générer le rapport HTML
    html_file = HTMLVisualizer.generate_html_report(
        clusters, equipment_names, equipment_recipes, equipment_data, 
        resource_names, similarity_scores, cluster_qualities
    )
    
    print(f"Rapport HTML généré: {html_file}")
    print("Ouvrez ce fichier dans votre navigateur pour visualiser les résultats.")

if __name__ == "__main__":
    main()