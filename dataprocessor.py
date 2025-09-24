from collections import defaultdict

class DataProcessor:
    @staticmethod
    def extract_equipment_data(equipments):
        equipment_names = []
        equipment_recipes = []
        equipment_data = {}
        recipe_ids = []
        unique_resource_ids = set()

        for equipment in equipments:
            equipment_name = equipment["name"]
            equipment_names.append(equipment_name)
            recipe = equipment.get("recipe", [])
            ids = [item["item_ankama_id"] for item in recipe]
            recipe_ids.append(ids)
            equipment_recipes.append(recipe)
            equipment_data[equipment_name] = equipment
            
            for item in recipe:
                if item["item_subtype"] == "resources":
                    unique_resource_ids.add(item["item_ankama_id"])

        return equipment_names, equipment_recipes, equipment_data, recipe_ids, unique_resource_ids

    @staticmethod
    def calculate_similarity_score(recipe1, recipe2):
        """
        Calcule le score de similarité entre deux recettes
        Utilise le coefficient de Jaccard: |A ∩ B| / |A ∪ B|
        """
        # Extraire les IDs des ressources des deux recettes
        resources1 = {item["item_ankama_id"] for item in recipe1 if item["item_subtype"] == "resources"}
        resources2 = {item["item_ankama_id"] for item in recipe2 if item["item_subtype"] == "resources"}
        
        # Éviter la division par zéro
        if not resources1 and not resources2:
            return 0
        
        # Calculer le coefficient de Jaccard
        intersection = resources1 & resources2
        union = resources1 | resources2
        
        return len(intersection) / len(union)
    
    @staticmethod
    def calculate_weighted_similarity_score(recipe1, recipe2):
        """
        Calcule un score de similarité pondéré qui tient compte des quantités
        Les ressources qui apparaissent en grande quantité ont plus de poids
        """
        # Créer des dictionnaires de quantité par ressource
        quantities1 = {}
        quantities2 = {}
        
        for item in recipe1:
            if item["item_subtype"] == "resources":
                item_id = item["item_ankama_id"]
                quantities1[item_id] = quantities1.get(item_id, 0) + item["quantity"]
        
        for item in recipe2:
            if item["item_subtype"] == "resources":
                item_id = item["item_ankama_id"]
                quantities2[item_id] = quantities2.get(item_id, 0) + item["quantity"]
        
        # Éviter la division par zéro
        if not quantities1 and not quantities2:
            return 0
        
        # Calculer la similarité pondérée
        common_resources = set(quantities1.keys()) & set(quantities2.keys())
        total_resources = set(quantities1.keys()) | set(quantities2.keys())
        
        if not total_resources:
            return 0
        
        # Pondération basée sur les quantités minimales
        weighted_intersection = sum(min(quantities1.get(r, 0), quantities2.get(r, 0)) for r in common_resources)
        weighted_union = sum(max(quantities1.get(r, 0), quantities2.get(r, 0)) for r in total_resources)
        
        return weighted_intersection / weighted_union if weighted_union > 0 else 0
    
    @staticmethod
    def build_similarity_graph_with_scores(equipment_names, equipment_recipes, min_similarity=0.3):
        """
        Construit un graphe de similarité avec des scores basés sur la similarité des recettes
        """
        graph = defaultdict(list)
        similarity_scores = {}
        
        for i in range(len(equipment_names)):
            for j in range(i + 1, len(equipment_names)):
                # Calculer le score de similarité
                similarity = DataProcessor.calculate_weighted_similarity_score(
                    equipment_recipes[i], equipment_recipes[j]
                )
                
                # Ajouter une arête si la similarité dépasse le seuil
                if similarity >= min_similarity:
                    graph[equipment_names[i]].append((equipment_names[j], similarity))
                    graph[equipment_names[j]].append((equipment_names[i], similarity))
                    similarity_scores[(equipment_names[i], equipment_names[j])] = similarity
        
        return graph, similarity_scores

    @staticmethod
    def find_optimal_clusters(graph, equipment_names, min_cluster_size=2):
        """
        Trouve des clusters optimaux en utilisant un algorithme glouton
        qui maximise la similarité moyenne à l'intérieur des clusters
        """
        clusters = []
        visited = set()
        
        # Trier les équipements par degré de connectivité (nombre de voisins)
        sorted_equipments = sorted(
            equipment_names,
            key=lambda x: len(graph.get(x, [])),
            reverse=True
        )
        
        for equipment in sorted_equipments:
            if equipment in visited:
                continue
                
            # Créer un nouveau cluster autour de cet équipement
            cluster = [equipment]
            visited.add(equipment)
            
            # Trouver tous les voisins non visités avec une similarité élevée
            neighbors = graph.get(equipment, [])
            sorted_neighbors = sorted(neighbors, key=lambda x: x[1], reverse=True)
            
            for neighbor, similarity in sorted_neighbors:
                if neighbor not in visited:
                    cluster.append(neighbor)
                    visited.add(neighbor)
            
            # Ne garder que les clusters d'une taille minimale
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
        
        return clusters

    @staticmethod
    def evaluate_cluster_quality(cluster, equipment_names, equipment_recipes, resource_names):
        """
        Évalue la qualité d'un cluster basée sur:
        1. Le pourcentage de ressources partagées
        2. L'économie d'échelle potentielle
        3. La similarité moyenne entre les équipements
        """
        # Calculer toutes les ressources du cluster
        all_resources = defaultdict(int)
        equipment_resources = []
        
        for eq_name in cluster:
            index = equipment_names.index(eq_name)
            resources = {}
            for item in equipment_recipes[index]:
                if item["item_subtype"] == "resources":
                    item_id = item["item_ankama_id"]
                    quantity = item["quantity"]
                    resources[item_id] = quantity
                    all_resources[item_id] += quantity
            equipment_resources.append(resources)
        
        # Calculer le pourcentage de ressources partagées
        shared_resources = 0
        for resource_id, total_quantity in all_resources.items():
            # Une ressource est considérée comme partagée si elle apparaît dans au moins 2 équipements
            count = sum(1 for resources in equipment_resources if resource_id in resources)
            if count >= 2:
                shared_resources += total_quantity
        
        total_resources = sum(all_resources.values())
        sharing_percentage = (shared_resources / total_resources) * 100 if total_resources > 0 else 0
        
        # Calculer la similarité moyenne dans le cluster
        total_similarity = 0
        pair_count = 0
        
        for i in range(len(cluster)):
            for j in range(i + 1, len(cluster)):
                idx_i = equipment_names.index(cluster[i])
                idx_j = equipment_names.index(cluster[j])
                similarity = DataProcessor.calculate_weighted_similarity_score(
                    equipment_recipes[idx_i], equipment_recipes[idx_j]
                )
                total_similarity += similarity
                pair_count += 1
        
        avg_similarity = total_similarity / pair_count if pair_count > 0 else 0
        
        # Calculer l'économie potentielle (réduction des doublons)
        economy_score = sharing_percentage / 100
        
        return {
            'sharing_percentage': sharing_percentage,
            'avg_similarity': avg_similarity,
            'economy_score': economy_score,
            'total_resources': total_resources,
            'shared_resources': shared_resources,
            'unique_resources': len(all_resources)
        }
    @staticmethod
    def calculate_cluster_resources(cluster, equipment_names, equipment_recipes, resource_names):
        """
        Calculate the total resources needed for a cluster of equipment.
        Returns equipment details, sorted ingredients, and total resources.
        
        Args:
            cluster: List of equipment names in the cluster
            equipment_names: List of all equipment names
            equipment_recipes: List of all equipment recipes
            resource_names: Dictionary mapping resource IDs to resource names
        
        Returns:
            tuple: (equipment_details, sorted_ingredients, total_resources)
        """
        equipment_details = []
        cluster_resources = defaultdict(int)
        
        # Process each equipment in the cluster
        for eq_name in cluster:
            if eq_name in equipment_names:
                index = equipment_names.index(eq_name)
                recipe = equipment_recipes[index]
                
                # Collect equipment details
                eq_detail = {
                    'name': eq_name,
                    'ingredients': []
                }
                
                # Process each ingredient
                for item in recipe:
                    if item["item_subtype"] == "resources":
                        resource_id = item["item_ankama_id"]
                        quantity = item["quantity"]
                        
                        # Get resource name from ID, or use ID if name not found
                        resource_name = resource_names.get(resource_id, f"Resource_{resource_id}")
                        
                        # Add to equipment details
                        eq_detail['ingredients'].append({
                            'name': resource_name,
                            'quantity': quantity
                        })
                        
                        # Add to total cluster resources
                        cluster_resources[resource_name] += quantity
                
                equipment_details.append(eq_detail)
        
        # Sort ingredients by quantity (descending)
        sorted_ingredients = sorted(
            cluster_resources.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        total_resources = sum(cluster_resources.values())
        
        return equipment_details, sorted_ingredients, total_resources