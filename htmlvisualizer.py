from datetime import datetime
from config import Config
from dataprocessor import DataProcessor

class HTMLVisualizer:
    @staticmethod
    def generate_html_report(clusters, equipment_names, equipment_recipes, equipment_data, 
                            resource_names, similarity_scores, cluster_qualities=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/{Config.OUTPUT_PREFIX}_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <meta charset="UTF-8">
                <title>Groupes de Crafting Dofus</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                    .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                    .cluster { background-color: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .equipment { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-left: 4px solid #3498db; }
                    .resources { margin: 10px 0; }
                    .resource-item { padding: 5px; margin: 2px; background-color: #e7f4ff; display: inline-block; border-radius: 3px; }
                    .common-items { margin: 10px 0; }
                    .summary { background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .progress-bar { background-color: #e0e0e0; border-radius: 5px; margin: 5px 0; }
                    .progress-fill { background-color: #4caf50; height: 20px; border-radius: 5px; text-align: center; color: white; }
                    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                    th { background-color: #f2f2f2; }
                    .toggle { cursor: pointer; color: #3498db; }
                    .quality-info { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
                    .quality-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
                    .metric { display: flex; flex-direction: column; }
                    .metric-label { font-weight: bold; margin-bottom: 5px; }
                    .metric-value { font-size: 1.1em; margin-bottom: 5px; }
                </style>
                <script>
                    function toggleVisibility(id) {
                        var element = document.getElementById(id);
                        if (element.style.display === 'none') {
                            element.style.display = 'block';
                        } else {
                            element.style.display = 'none';
                        }
                    }
                </script>
            </head>
            <body>
                <div class="header">
                    <h1>Analyse de Groupes de Crafting Dofus</h1>
                    <p>Date: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                    <p>Niveaux: """ + str(Config.MIN_LEVEL) + """-""" + str(Config.MAX_LEVEL) + """</p>
                    <p>Objets communs minimum: """ + str(Config.MIN_COMMON_ITEMS) + """</p>
                    <p>Total équipements analysés: """ + str(len(equipment_names)) + """</p>
                    <p>Groupes trouvés: """ + str(len(clusters)) + """</p>
                </div>
            """)
            
            if clusters:
                for i, cluster in enumerate(clusters, 1):
                    # Récupérer les informations de qualité si disponibles
                    quality_info = None
                    if cluster_qualities and i <= len(cluster_qualities):
                        quality_info = cluster_qualities[i-1]
                    
                    equipment_details, sorted_ingredients, total_resources = DataProcessor.calculate_cluster_resources(
                        cluster, equipment_names, equipment_recipes, resource_names
                    )
                    
                    f.write(f"""
                    <div class="cluster">
                        <h2>Groupe {i} ({len(cluster)} équipements)</h2>
                    """)
                    
                    # Afficher les informations de qualité
                    if quality_info:
                        f.write(f"""
                        <div class="quality-info">
                            <h3>Qualité du groupe</h3>
                            <div class="quality-metrics">
                                <div class="metric">
                                    <span class="metric-label">Ressources partagées:</span>
                                    <span class="metric-value">{quality_info['sharing_percentage']:.1f}%</span>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: {quality_info['sharing_percentage']}%"></div>
                                    </div>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Similarité moyenne:</span>
                                    <span class="metric-value">{quality_info['avg_similarity']:.2f}</span>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: {quality_info['avg_similarity']*100}%"></div>
                                    </div>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Score d'économie:</span>
                                    <span class="metric-value">{quality_info['economy_score']:.2f}</span>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: {quality_info['economy_score']*100}%"></div>
                                    </div>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Ressources totales:</span>
                                    <span class="metric-value">{quality_info['total_resources']}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label">Ressources uniques:</span>
                                    <span class="metric-value">{quality_info['unique_resources']}</span>
                                </div>
                            </div>
                        </div>
                        """)
                    
                    # Équipements du groupe
                    f.write("""
                        <h3 class="toggle" onclick="toggleVisibility('equipments""" + str(i) + """')">▼ Équipements du groupe</h3>
                        <div id="equipments""" + str(i) + """">
                    """)
                    
                    for detail in equipment_details:
                        equipment = equipment_data[detail['name']]
                        level = equipment.get('level', 'N/A')
                        equipment_type = equipment.get('type', {}).get('name', 'N/A')
                        
                        f.write(f"""
                            <div class="equipment">
                                <h4>{detail['name']} (Niveau {level}, {equipment_type})</h4>
                                <div class="resources">
                        """)
                        
                        if detail['recipe']:
                            for item in detail['recipe']:
                                f.write(f"""
                                    <div class="resource-item">{item['name']}: {item['quantity']}</div>
                                """)
                        else:
                            f.write("<p>Aucune recette disponible</p>")
                        
                        f.write("""
                                </div>
                            </div>
                        """)
                    
                    f.write("</div>")
                    
                    # Ingrédients totaux
                    f.write("""
                        <h3 class="toggle" onclick="toggleVisibility('ingredients""" + str(i) + """')">▼ Ingrédients totaux</h3>
                        <div id="ingredients""" + str(i) + """">
                            <table>
                                <tr>
                                    <th>Ressource</th>
                                    <th>Quantité</th>
                                    <th>Pourcentage</th>
                                    <th>Progression</th>
                                </tr>
                    """)
                    
                    for item_id, quantity in sorted_ingredients:
                        resource_name = resource_names.get(item_id, f"{item_id}")
                        percentage = (quantity / total_resources) * 100
                        
                        f.write(f"""
                            <tr>
                                <td>{resource_name}</td>
                                <td>{quantity}</td>
                                <td>{percentage:.1f}%</td>
                                <td>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: {percentage}%">{percentage:.1f}%</div>
                                    </div>
                                </td>
                            </tr>
                        """)
                    
                    f.write("""
                            </table>
                        </div>
                    """)
                    
                    f.write("</div>")
            
            else:
                f.write("""
                <div class="cluster">
                    <h2>Aucun groupe trouvé</h2>
                    <p>Aucun groupe ne partage au moins """ + str(Config.MIN_COMMON_ITEMS) + """ objets communs.</p>
                </div>
                """)
            
            f.write("""
            </body>
            </html>
            """)
        
        print(f"Rapport HTML généré: {filename}")
        return filename
