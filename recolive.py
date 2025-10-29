# reconocer_en_vivo.py
import cv2
import json
import time
import numpy as np
import face_recognition
from pathlib import Path

# === Fuente de video ===
# 1) Stream directo de tu ESP32-CAM (LAN):
# STREAM_URL = "http://192.168.18.30:81/stream"

# 2) Si ya usas broker RTSP (MediaMTX), usa la URL pública RTSP:
# STREAM_URL = "rtsp://<IP_o_dominio_del_broker>:8554/esp32"

# ---- Elige UNA y descomenta:
STREAM_URL = "http://192.168.18.30:81/stream"

# === Archivos de embeddings ===
ENCODINGS_NPY = "encodings.npy"
LABELS_JSON   = "labels.json"

# Umbral de decisión (distancia euclídea). 0.6–0.62 suele ser razonable.
THRESHOLD = 0.6

# Para acelerar: redimensionar frame antes de detectar/encodear (0.5 = mitad)
DOWNSCALE = 0.5

def load_encodings():
    if not Path(ENCODINGS_NPY).exists() or not Path(LABELS_JSON).exists():
        raise SystemExit("No encuentro encodings.npy o labels.json. Corre primero crear_embeddings.py")

    encs = np.load(ENCODINGS_NPY)  # shape (N, 128)
    with open(LABELS_JSON, "r", encoding="utf-8") as f:
        labels = json.load(f)

    if encs.dtype != np.float32:
        encs = encs.astype(np.float32)

    if len(encs) != len(labels):
        raise SystemExit("Inconsistencia: encodings.npy y labels.json tienen diferente tamaño.")

    return encs, labels

def best_match(unknown_enc: np.ndarray, known_encs: np.ndarray, labels: list, thr=THRESHOLD):
    # Distancia euclídea a todos los encodings conocidos
    dists = np.linalg.norm(known_encs - unknown_enc.astype(np.float32), axis=1)
    idx = int(np.argmin(dists))
    name = labels[idx]
    dist = float(dists[idx])
    if dist <= thr:
        return name, dist
    return "Desconocido", dist

def main():
    known_encs, labels = load_encodings()
    print(f"✅ Encodings cargados: {len(labels)} personas")

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el stream (revisa la URL y conectividad).")

    fps_smooth = None
    t0 = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Redimensionar para acelerar
        small = cv2.resize(frame, (0, 0), fx=DOWNSCALE, fy=DOWNSCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # Detectar y encodear
        boxes = face_recognition.face_locations(rgb_small, model="hog")
        encs = face_recognition.face_encodings(rgb_small, boxes)

        # Escalar cajas a tamaño original
        boxes_scaled = []
        for (t, r, b, l) in boxes:
            boxes_scaled.append((
                int(t / DOWNSCALE), int(r / DOWNSCALE),
                int(b / DOWNSCALE), int(l / DOWNSCALE)
            ))

        # Matcher
        for (t, r, b, l), enc in zip(boxes_scaled, encs):
            name, dist = best_match(enc, known_encs, labels, THRESHOLD)

            # Dibujar
            cv2.rectangle(frame, (l, t), (r, b), (0, 255, 0), 2)
            text = f"{name} ({dist:.2f})"
            (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            y = max(t - 10, h + 10)
            cv2.rectangle(frame, (l, y - h - baseline), (l + w, y + baseline//2), (0, 255, 0), -1)
            cv2.putText(frame, text, (l, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # FPS simple
        t1 = time.time()
        fps = 1.0 / (t1 - t0) if t1 > t0 else 0.0
        fps_smooth = fps if fps_smooth is None else (0.9 * fps_smooth + 0.1 * fps)
        t0 = t1
        cv2.putText(frame, f"FPS: {fps_smooth:.1f}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Reconocimiento en vivo", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC para salir
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
