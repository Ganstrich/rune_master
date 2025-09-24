# resourceoptimizer.py
from collections import defaultdict, Counter
import operator

class ResourceOptimizer:
    @staticmethod
    def find_optimal_equipment_sets(equipment_names, equipment_recipes, resource_names, max_resources=15):
        """
        Trouve les ensembles d'équipements qui maximisent le nombre d'items craftables
        tout en minimisant le nombre de ressources distinctes nécessaires.
        
        Args:
            equipment_names: Liste des noms d'équipements
            equipment_recipes: Liste des recettes d'équipements
            resource_names: Dictionnaire des noms de ressources
            max_resources: Nombre maximum de ressources à considérer
            
        Returns:
            Liste des ensembles d'équipements optimaux triés par efficacité
        """
        # Calculer les ressources utilisées par chaque équipement
        equipment_resources = {}
        for i, eq_name in enumerate(equipment_names):
            resources = set()
            for item in equipment_recipes[i]:
                if item["item_subtype"] == "resources":
                    resources.add(item["item_ankama_id"])
            equipment_resources[eq_name] = resources
        
        # Calculer la fréquence de chaque ressource
        resource_frequency = Counter()
        for resources in equipment_resources.values():
            resource_frequency.update(resources)
        
        # Trouver les ressources les plus courantes
        most_common_resources = [res for res, count in resource_frequency.most_common(max_resources)]
        
        # Trouver les équipements qui utilisent principalement ces ressources
        optimal_sets = []
        for i in range(5, max_resources + 1, 5):  # Essayer différentes tailles de sets de ressources
            current_resources = set(most_common_resources[:i])
            
            # Trouver les équipements qui peuvent être craftés avec ces ressources
            craftable_equipments = []
            for eq_name, resources in equipment_resources.items():
                if resources.issubset(current_resources):
                    craftable_equipments.append(eq_name)
            
            if craftable_equipments:
                # Calculer l'efficacité (nombre d'équipements / nombre de ressources)
                efficiency = len(craftable_equipments) / i
                optimal_sets.append({
                    'resources': current_resources,
                    'equipments': craftable_equipments,
                    'efficiency': efficiency,
                    'resource_count': i,
                    'equipment_count': len(craftable_equipments)
                })
        
        # Trier par efficacité
        optimal_sets.sort(key=lambda x: x['efficiency'], reverse=True)
        return optimal_sets
    
    @staticmethod
    def generate_optimization_report(optimal_sets, resource_names, equipment_data, filename="resource_optimization.html"):
        """
        Génère un rapport HTML des ensembles d'équipements optimaux
        
        Args:
            optimal_sets: Liste des ensembles optimaux
            resource_names: Dictionnaire des noms de ressources
            equipment_data: Dictionnaire des données d'équipements
            filename: Nom du fichier de sortie
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <title>Optimisation des Ressources de Crafting Dofus</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                    .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                    .set { background-color: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .efficiency { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
                    .resources, .equipments { margin: 10px 0; }
                    .resource-item, .equipment-item { padding: 5px; margin: 2px; background-color: #e7f4ff; display: inline-block; border-radius: 3px; }
                    .equipment-item { background-color: #e8f5e9; }
                    .summary { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Optimisation des Ressources de Crafting Dofus</h1>
                    <p>Ensembles d'équipements avec ressources partagées maximales</p>
                </div>
            """)
            
            for i, optimal_set in enumerate(optimal_sets, 1):
                f.write(f"""
                <div class="set">
                    <h2>Ensemble Optimal #{i}</h2>
                    <div class="efficiency">
                        Efficacité: {optimal_set['efficiency']:.2f} 
                        ({optimal_set['equipment_count']} équipements / {optimal_set['resource_count']} ressources)
                    </div>
                    
                    <h3>Ressources nécessaires:</h3>
                    <div class="resources">
                """)
                
                for resource_id in optimal_set['resources']:
                    resource_name = resource_names.get(resource_id, f"Ressource {resource_id}")
                    f.write(f'<div class="resource-item">{resource_name}</div>')
                
                f.write("""
                    </div>
                    
                    <h3>Équipements craftables:</h3>
                    <div class="equipments">
                """)
                
                for eq_name in optimal_set['equipments']:
                    equipment = equipment_data.get(eq_name, {})
                    level = equipment.get('level', 'N/A')
                    eq_type = equipment.get('type', {}).get('name', 'N/A')
                    f.write(f'<div class="equipment-item">{eq_name} (Niv. {level}, {eq_type})</div>')
                
                f.write("""
                    </div>
                </div>
                """)
            
            f.write("""
            </body>
            </html>
            """)
        
        print(f"Rapport d'optimisation généré: {filename}")
        return filename