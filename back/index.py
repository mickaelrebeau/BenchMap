import overpy
import json
import csv
import os
import requests
from decimal import Decimal
import time
# from Mapillary import get_bench_from_mapillary
from StreetView import get_bench_from_streetview_yolo

# Install yolov5 first

# git clone https://github.com/ultralytics/yolov5.git
# cd yolov5
# pip install -r requirements.txt

# === Timer ===
start_time = time.time()
print("🚀 Démarrage du script...")

WIKI_SEARCH_QUERY = "public bench Paris"
MAX_WIKI_IMAGES = 20000  # limiter pour éviter les abus

# === SETUP ===
os.makedirs("images", exist_ok=True)
api = overpy.Overpass()

query = """
node
  ["amenity"="bench"]
  (48.8156, 2.2241, 48.9022, 2.4699);
out body;
"""

print("📡 Récupération des bancs depuis OpenStreetMap...")
result = api.query(query)
print(f"✅ {len(result.nodes)} bancs trouvés sur OpenStreetMap")

# === Wikimedia fallback search ===
print("\n🔍 Recherche des images sur Wikimedia Commons...")
def get_wikimedia_bench_images(limit=1000):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": "file:bench",
        "gsrnamespace": 6,  
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 800
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        image_urls = []

        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                thumb_url = imageinfo[0].get("thumburl")
                if thumb_url:
                    image_urls.append(thumb_url)

        return image_urls

    except Exception as e:
        print(f"Erreur Wikimedia API: {e}")
        return []

wikimedia_images = get_wikimedia_bench_images(MAX_WIKI_IMAGES)
wiki_image_index = 0  # pour attribuer une image différente à chaque banc sans doublon

print(f"✅ {len(wikimedia_images)} images trouvées sur Wikimedia Commons")

# === Traitement des bancs ===
print("\n🔄 Traitement des bancs et téléchargement des images...")
benches_data = []
total_benches = len(result.nodes)

for i, node in enumerate(result.nodes, 1):
    if i % 1000 == 0:  # Affiche la progression tous les 1000 bancs
        print(f"⏳ Progression : {i}/{total_benches} bancs traités ({(i/total_benches*100):.1f}%)")
    
    tags = node.tags
    photo_url = ""

    # Cas 1 : lien direct dans les tags OSM
    if "image" in tags:
        image_url = tags["image"]
        if image_url.startswith("http"):
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    ext = image_url.split(".")[-1].split("?")[0]
                    local_path = f"images/bench_{node.id}.{ext}"
                    with open(local_path, "wb") as f_img:
                        f_img.write(response.content)
                    photo_url = local_path
            except Exception as e:
                print(f"⚠️ Erreur image directe pour banc {node.id}: {e}")

    # Cas 2 : fallback Wikimedia Commons
    if not photo_url and wiki_image_index < len(wikimedia_images):
        try:
            image_url = wikimedia_images[wiki_image_index]
            ext = image_url.split(".")[-1].split("?")[0].split("/")[0]
            local_path = f"images/bench_{node.id}.{ext}"
            search_terms = ["file:bench", "file:park bench", "file:public seating", "file:street furniture"]

            params = {
                "search_terms": json.dumps(search_terms)
            }
            response = requests.get(image_url, params=params, timeout=10)
            
            if response.status_code == 200:
                with open(local_path, "wb") as f_img:
                    f_img.write(response.content)
                photo_url = local_path
                wiki_image_index += 1
        except Exception as e:
            print(f"⚠️ Erreur image Wikimedia pour banc {node.id}: {e}")

    # # Cas 3 : fallback Mapillary + YOLO (si pas d'image encore)
    # if not photo_url:
    #     lat = float(node.lat)
    #     lon = float(node.lon)

    #     photo_url = get_bench_from_mapillary(
    #         lat, lon, node.id,
    #             lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001
    #         )

    if not photo_url:
        photo_url = get_bench_from_streetview_yolo(node.lat, node.lon, node.id)

    bench = {
        "id": node.id,
        "latitude": node.lat,
        "longitude": node.lon,
        "tags": tags,
        "photo_url": photo_url
    }
    benches_data.append(bench)

print(f"\n✅ Traitement terminé !")
print(f"📊 Statistiques finales :")
print(f"   - Nombre de bancs récupérés : {len(benches_data)}")
print(f"   - Images Wikimedia utilisées : {wiki_image_index}/{MAX_WIKI_IMAGES}")

# === Sauvegarde JSON ===
print("\n💾 Sauvegarde des données en JSON...")
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

with open("benches_paris.json", "w", encoding="utf-8") as f_json:
    json.dump(benches_data, f_json, ensure_ascii=False, indent=2, cls=DecimalEncoder)

# === Sauvegarde CSV ===
print("💾 Sauvegarde des données en CSV...")
all_tag_keys = set()
for bench in benches_data:
    all_tag_keys.update(bench["tags"].keys())

fieldnames = ["id", "latitude", "longitude", "photo_url"] + sorted(all_tag_keys)

with open("benches_paris.csv", "w", newline="", encoding="utf-8") as f_csv:
    writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
    writer.writeheader()

    for bench in benches_data:
        row = {
            "id": bench["id"],
            "latitude": bench["latitude"],
            "longitude": bench["longitude"],
            "photo_url": bench["photo_url"]
        }
        for tag in all_tag_keys:
            row[tag] = bench["tags"].get(tag, "")
        writer.writerow(row)

# === Fin du timer ===
end_time = time.time()
execution_time = end_time - start_time
print(f"\n⏱️ Temps d'exécution total : {execution_time:.2f} secondes")
print("✨ Script terminé avec succès !")
