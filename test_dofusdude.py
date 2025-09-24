import requests

language = 'fr'
game = 'dofus3'
url = f"https://api.dofusdu.de/{game}/v1/{language}/items/equipment/all"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Erreur lors de la requête : {response.status_code}")
