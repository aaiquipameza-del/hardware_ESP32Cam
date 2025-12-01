# registrar_3shots.py
import os
import time
import json
import cv2
import numpy as np
import face_recognition
import requests
from pathlib import Path

# === Configuración de cámara ===
STREAM_URL = "http://192.168.122.116:81/stream"

# Endpoints del flash (ajústalos a tu firmware/CameraWebServer si aplica)
FLASH_ON_URL  = "http://192.168.122.116/control?var=led_intensity&val=255"
FLASH_OFF_URL = "http://192.168.122.116/control?var=led_intensity&val=0"

# === Almacenamiento ===
SAVE_IMAGES = False
IMAGES_DIR = "capturas_registro"  # se creará <IMAGES_DIR>/<Nombre>/
ENCODINGS_NPY = "encodings.npy"   # matriz (N,128) acumulada
LABELS_JSON   = "labels.json"     # lista de N nombres alineados

# === Parámetros del registro ===
N_SAMPLES = 3            # cuántos embeddings por persona
MAX_TRIES_PER_SAMPLE = 8 # reintentos si no detecta rostro
DOWNSCALE_DETECT = 0.7   # acelerar detección (0.5-0.8 razonable)
DELAY_FLASH = 0.15       # segundo(s) de flash antes de capturar

def ensure_dirs():
    os.makedirs(IMAGES_DIR, exist_ok=True)

def flash(on=True):
    try:
        url = FLASH_ON_URL if on else FLASH_OFF_URL
        requests.get(url, timeout=0.7)
    except Exception:
        # si no hay endpoint/firmware compatible, simplemente ignora
        pass

def detect_largest_face_and_encode(frame_bgr):
    """Devuelve (encoding(128,), box) o (None, None) si falla."""
    # downscale para detectar más rápido
    small = cv2.resize(frame_bgr, (0, 0), fx=DOWNSCALE_DETECT, fy=DOWNSCALE_DETECT)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb_small, model="hog")
    if not boxes:
        return None, None
    # ordena por área y toma la más grande
    boxes = sorted(boxes, key=lambda b: (b[2]-b[0])*(b[1]-b[3]), reverse=True)
    encs = face_recognition.face_encodings(rgb_small, [boxes[0]])
    if not encs:
        return None, None
    # escala la caja a tamaño original (opcional si quieres dibujar)
    (t, r, b, l) = boxes[0]
    box_full = (int(t / DOWNSCALE_DETECT), int(r / DOWNSCALE_DETECT),
                int(b / DOWNSCALE_DETECT), int(l / DOWNSCALE_DETECT))
    return encs[0], box_full

def append_to_master(enc_list, name):
    """Agrega 1..k encodings de 'name' a (ENCODINGS_NPY, LABELS_JSON)."""
    # cargar existentes si hay
    if Path(ENCODINGS_NPY).exists():
        enc_master = np.load(ENCODINGS_NPY)
        if enc_master.ndim == 1:  # corner case si hay 1 solo
            enc_master = enc_master.reshape(1, -1)
        labels = json.loads(Path(LABELS_JSON).read_text(encoding="utf-8"))
    else:
        enc_master = np.zeros((0, 128), dtype=np.float32)
        labels = []
    # apilar
    enc_new = np.vstack([e.astype(np.float32) for e in enc_list])
    enc_all = np.vstack([enc_master, enc_new]) if enc_master.size else enc_new
    labels += [name] * len(enc_list)
    # guardar
    np.save(ENCODINGS_NPY, enc_all)
    Path(LABELS_JSON).write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    return enc_all.shape[0], len(labels)

def main():
    ensure_dirs()
    print("✅ Listo. Presiona 'R' para registrar a una persona (3 capturas). ESC para salir.")
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el stream. Revisa la IP/puertos.")

    registering = False
    name = None
    person_dir = None
    sample_count = 0
    collected = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Dibujo de guía (opcional): detecta solo para mostrar recuadro
        enc_preview, box = detect_largest_face_and_encode(frame)
        if box:
            (t, r, b, l) = box
            cv2.rectangle(frame, (l, t), (r, b), (0, 255, 0), 2)
            cv2.putText(frame, "R = Registrar (3 capturas)", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        if registering:
            cv2.putText(frame, f"Registrando {name}: muestra {sample_count+1}/{N_SAMPLES}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.imshow("Registro 3-shots", frame)
        k = cv2.waitKey(1) & 0xFF

        if k == 27:  # ESC
            break

        if k == ord('r') and not registering:
            # pide nombre en consola
            try:
                # cerrar ventana de OpenCV para que no robe foco del input (opcional)
                # cv2.destroyWindow("Registro 3-shots")
                name = input("\n>>> Ingresa el NOMBRE de la persona: ").strip()
            except Exception:
                name = "SinNombre"
            if not name:
                name = "SinNombre"
            person_dir = os.path.join(IMAGES_DIR, name)
            os.makedirs(person_dir, exist_ok=True)
            registering = True
            sample_count = 0
            collected = []
            print(f"--> Registrando a {name} (se capturarán {N_SAMPLES} embeddings)")

        # ciclo de captura de 3 muestras
        if registering:
            # por cada muestra, ilumina/lee/reintenta hasta MAX_TRIES_PER_SAMPLE
            got = False
            tries = 0
            while tries < MAX_TRIES_PER_SAMPLE and not got:
                tries += 1
                flash(True)
                time.sleep(DELAY_FLASH)
                ok2, frame2 = cap.read()
                flash(False)
                if not ok2:
                    continue

                enc, box2 = detect_largest_face_and_encode(frame2)
                if enc is not None:
                    collected.append(enc)
                    sample_count += 1
                    got = True
                    # guardar imagen (opcional)
                    if SAVE_IMAGES:
                        filename = f"{name}_{sample_count:02d}.jpg"
                        cv2.imwrite(os.path.join(person_dir, filename), frame2)
                        print(f"📸 Guardada: {filename}")
                else:
                    print("   ⚠️ No se detectó rostro, reintentando...")

            if not got:
                print("   ❌ No se logró capturar rostro en esta muestra. Cancela con ESC o intenta de nuevo con R.")
                registering = False  # resetea el flujo para que el usuario presione R otra vez
                continue

            # ¿ya completó las N_SAMPLES?
            if sample_count >= N_SAMPLES:
                # Append a los maestros
                total_rows, total_labels = append_to_master(collected, name)
                print(f"✅ Registro completado para {name}.")
                print(f"   Se agregaron {N_SAMPLES} embeddings. Total en {ENCODINGS_NPY}: {total_rows}")
                # reset
                registering = False
                name = None
                person_dir = None
                sample_count = 0
                collected = []

    cap.release()
    cv2.destroyAllWindows()
    print("Cerrado.")

if __name__ == "__main__":
    main()
