import os
import torch
import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

def get_bench_from_streetview_yolo(lat, lon, bench_id, headings=(0, 90, 180, 270)):
    GOOGLE_API_KEY = os.getenv("GOOGLE_STREETVIEW_KEY")
    if not GOOGLE_API_KEY:
        print("❌ Clé API Google Street View manquante")
        return ""

    base_url = "https://maps.googleapis.com/maps/api/streetview"
    model = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True, verbose=False)

    for heading in headings:
        try:
            # 1. Récupération image depuis Google Street View
            params = {
                "size": "640x640",
                "location": f"{lat},{lon}",
                "fov": 90,
                "heading": heading,
                "pitch": 0,
                "radius": 50,
                "key": GOOGLE_API_KEY
            }

            response = requests.get(base_url, params=params)
            if response.status_code != 200 or response.content.startswith(b'<!DOCTYPE html>'):
                continue  # Aucun panorama dans cette direction

            img_path = f"streetview/streetview_{bench_id}_{heading}.jpg"
            with open(img_path, "wb") as f:
                f.write(response.content)

            # 2. Chargement et détection avec YOLO
            img = cv2.imread(img_path)
            results = model(img)
            detections = results.pandas().xyxy[0]

            for _, row in detections.iterrows():
                label = row["name"]
                conf = row["confidence"]
                if label in ["bench", "chair", "sofa"] and conf > 0.4:
                    xmin, ymin, xmax, ymax = map(int, [row["xmin"], row["ymin"], row["xmax"], row["ymax"]])
                    crop = img[ymin:ymax, xmin:xmax]
                    final_path = f"images/bench_{bench_id}_streetview.jpg"
                    cv2.imwrite(final_path, crop)
                    print(f"🪑 Banc détecté (YOLO + StreetView) pour banc {bench_id} (heading {heading})")
                    return final_path

        except Exception as e:
            print(f"⚠️ Erreur traitement StreetView heading {heading} : {e}")
            continue

    print(f"📭 Aucun banc détecté via Street View pour banc {bench_id}")
    return ""
