# --- PARCHE: forzar backend de video antes de importar cv2 ---
import os
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"   # preferir FFmpeg sobre MSMF
# os.environ["OPENCV_VIDEOIO_DEBUG"] = "1"        # (opcional) logs del backend

import cv2
import json
import time
import urllib.request
import numpy as np
import face_recognition
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# === Fuente de video ===
# STREAM_URL = "http://192.168.107.116/stream"     # ejemplo
STREAM_URL = "http://192.168.107.116/stream"         # corregido (sin doble /)

# === Archivos de embeddings ===
ENCODINGS_NPY = "encodings.npy"
LABELS_JSON   = "labels.json"

# Umbral de decisión (distancia euclídea)
THRESHOLD = 0.6

# Para acelerar
DOWNSCALE = 0.5

# ---------- PARCHE: lector MJPEG manual como fallback -----------
def mjpeg_frames(url, chunk_size=1024, timeout=5):
    req = urllib.request.urlopen(url, timeout=timeout)
    buf = b""
    while True:
        chunk = req.read(chunk_size)
        if not chunk:
            break
        buf += chunk
        a = buf.find(b"\xff\xd8")   # inicio JPEG
        b = buf.find(b"\xff\xd9")   # fin JPEG
        if a != -1 and b != -1 and b > a:
            jpg = buf[a:b+2]
            buf = buf[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame

class StreamWrapper:
    """Imita cap.read() de OpenCV usando el generador MJPEG."""
    def __init__(self, url):
        self._gen = mjpeg_frames(url)
    def read(self):
        try:
            frame = next(self._gen)
            return True, frame
        except StopIteration:
            return False, None

def open_stream_with_fallback(url):
    """
    Intenta abrir el stream en este orden:
      1) OpenCV+FFmpeg con URL tal cual
      2) OpenCV+FFmpeg con ?dummy=1
      3) OpenCV+FFmpeg probando puerto :81 si no estaba
      4) Lector MJPEG manual (StreamWrapper)
    Devuelve (cap, usado_wrapper: bool)
    """
    print(f"Intentando abrir stream con FFmpeg: {url}")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    def _is_open(c): return hasattr(c, "isOpened") and c.isOpened()

    if not _is_open(cap):
        alt = url + ("&dummy=1" if "?" in url else "?dummy=1")
        print(f"Reintentando con dummy param: {alt}")
        cap = cv2.VideoCapture(alt, cv2.CAP_FFMPEG)

    # Si la URL no especifica puerto, prueba con :81 (típico en CameraWebServer)
    if not _is_open(cap):
        try:
            pr = urlparse(url)
            host_has_port = (":" in pr.netloc.split("@")[-1])
            if not host_has_port:
                netloc = pr.netloc + ":81"
                url81 = urlunparse((pr.scheme, netloc, pr.path, pr.params, pr.query, pr.fragment))
                print(f"Reintentando en puerto :81 -> {url81}")
                cap = cv2.VideoCapture(url81, cv2.CAP_FFMPEG)
                if not _is_open(cap):
                    alt81 = url81 + ("&dummy=1" if "?" in url81 else "?dummy=1")
                    print(f"Reintentando :81 con dummy -> {alt81}")
                    cap = cv2.VideoCapture(alt81, cv2.CAP_FFMPEG)
        except Exception:
            pass

    if not _is_open(cap):
        print("⚠️ OpenCV no abrió el stream. Activando lector MJPEG manual…")
        return StreamWrapper(url), True

    ok, test_frame = cap.read()
    if not ok or test_frame is None:
        print("⚠️ OpenCV abrió pero no llega ningún frame. Usando lector MJPEG manual…")
        return StreamWrapper(url), True

    print("✅ Stream inicializado con OpenCV+FFmpeg")
    return cap, False
# ---------------------------------------------------------------

def load_encodings():
    if not Path(ENCODINGS_NPY).exists() or not Path(LABELS_JSON).exists():
        raise SystemExit("No encuentro encodings.npy o labels.json. Corre primero tu registrador.")

    encs = np.load(ENCODINGS_NPY)  # shape (N, 128)
    with open(LABELS_JSON, "r", encoding="utf-8") as f:
        labels = json.load(f)

    if encs.dtype != np.float32:
        encs = encs.astype(np.float32)

    if len(encs) != len(labels):
        raise SystemExit("Inconsistencia: encodings.npy y labels.json tienen diferente tamaño.")
    return encs, labels

def best_match(unknown_enc: np.ndarray, known_encs: np.ndarray, labels: list, thr=THRESHOLD):
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

    cap, used_wrapper = open_stream_with_fallback(STREAM_URL)

    fps_smooth = None
    t0 = time.time()

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            print("⚠️ Frame no válido; saliendo…")
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

    if hasattr(cap, "release"):
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
