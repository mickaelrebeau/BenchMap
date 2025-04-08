# https://www.mapillary.com/dashboard/developers

# git clone https://github.com/ultralytics/yolov5.git
# cd yolov5
# pip install -r requirements.txt

import requests
import cv2
import os
import torch

# === CONFIG ===
MAPILLARY_TOKEN = "TON_TOKEN_ICI"  # ← remplace avec ta clé
LAT, LON = 48.8584, 2.2945  # ex : Tour Eiffel
IMAGE_SIZE = 640  # Pour YOLO
OUTPUT_DIR = "detected_benches"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === 1. Chercher une image Mapillary proche ===
search_url = "https://graph.mapillary.com/images"
params = {
    "access_token": MAPILLARY_TOKEN,
    "fields": "id,thumb_1024_url",
    "closeto": f"{LON},{LAT}",
    "limit": 1
}

resp = requests.get(search_url, params=params)
data = resp.json()

if "data" not in data or len(data["data"]) == 0:
    print("❌ Aucune image trouvée autour de cette position.")
    exit()

img_url = data["data"][0]["thumb_1024_url"]
img_id = data["data"][0]["id"]
img_path = f"mapillary_{img_id}.jpg"

# === 2. Télécharger l’image ===
img_data = requests.get(img_url).content
with open(img_path, "wb") as f:
    f.write(img_data)

print(f"✅ Image téléchargée depuis Mapillary : {img_path}")

# === 3. Détection avec YOLOv5 ===
model = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True)
img = cv2.imread(img_path)

results = model(img)
detections = results.pandas().xyxy[0]

bench_count = 0
for i, row in detections.iterrows():
    label = row["name"]
    conf = row["confidence"]
    if label in ["bench", "chair", "sofa"]:  
        xmin, ymin, xmax, ymax = map(int, [row["xmin"], row["ymin"], row["xmax"], row["ymax"]])
        crop = img[ymin:ymax, xmin:xmax]
        filename = f"{OUTPUT_DIR}/bench_{img_id}_{bench_count}.jpg"
        cv2.imwrite(filename, crop)
        print(f"🪑 Banc détecté : {filename} (confiance: {conf:.2f})")
        bench_count += 1

if bench_count == 0:
    print("😕 Aucun banc détecté sur cette image.")
else:
    print(f"🎉 Total : {bench_count} banc(s) détecté(s).")

