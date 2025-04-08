from dotenv import load_dotenv
import os
import requests
# === CONFIG ===
load_dotenv('../back/.env')
MAPILLARY_TOKEN = os.getenv('MAPILLARY_TOKEN')

if not MAPILLARY_TOKEN:
    raise ValueError("❌ Token Mapillary non trouvé dans le fichier .env")

# === Mapillary fallback search ===
print("\n🔍 Recherche des images sur Mapillary...")
def get_bench_from_mapillary(lat, lon, bench_id, bbox_lon_x, bbox_lat_x, bbox_lon_y, bbox_lat_y):
    try:
        url = "https://graph.mapillary.com/images"
        params = {
            "access_token": MAPILLARY_TOKEN,
            "bbox": f"{bbox_lon_x},{bbox_lat_x},{bbox_lon_y},{bbox_lat_y}",
            "fields": "id,geometry,thumb_1024_url",
            "closeto": f"{lon},{lat}",
            "limit": 1
        }
        print(params)
        resp = requests.get(url, params=params)
        print(resp.json())
        data = resp.json()

        if "data" not in data or len(data["data"]) == 0:
            return ""

        img_url = data["data"][0]["thumb_1024_url"]
        img_id = data["data"][0]["id"]
        img_path = f"images/mapillary_{bench_id}_{img_id}.jpg"

        # Télécharger l'image
        img_data = requests.get(img_url).content
        with open(img_path, "wb") as f:
            f.write(img_data)

        # YOLO detection
        import torch
        import cv2

        model = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True, verbose=False)
        img = cv2.imread(img_path)
        results = model(img)
        detections = results.pandas().xyxy[0]

        for i, row in detections.iterrows():
            label = row["name"]
            conf = row["confidence"]
            if label in ["bench", "chair", "sofa"] and conf > 0.4:
                # Crop et sauvegarde
                xmin, ymin, xmax, ymax = map(int, [row["xmin"], row["ymin"], row["xmax"], row["ymax"]])
                crop = img[ymin:ymax, xmin:xmax]
                final_path = f"images/bench_{bench_id}_mapillary.jpg"
                cv2.imwrite(final_path, crop)
                return final_path

        return ""

    except Exception as e:
        print(f"⚠️ Erreur Mapillary/YOLO pour banc {bench_id}: {e}")
        return ""
