#!/usr/bin/env python3
import os
import time
import json
import cv2
import numpy as np
import face_recognition
import argparse
from pathlib import Path

# Simple headless registration script for integration with web UI.
# Usage: python register_headless.py --name "Nombre" --samples 3

STREAM_URL = "http://192.168.122.116:81/stream"
ENCODINGS_NPY = "encodings.npy"
LABELS_JSON = "labels.json"
IMAGES_DIR = "capturas_registro"

N_SAMPLES = 3
MAX_TRIES_PER_SAMPLE = 8
DOWNSCALE_DETECT = 0.7

def ensure_dirs():
    os.makedirs(IMAGES_DIR, exist_ok=True)

def detect_largest_face_and_encode(frame_bgr):
    small = cv2.resize(frame_bgr, (0, 0), fx=DOWNSCALE_DETECT, fy=DOWNSCALE_DETECT)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb_small, model="hog")
    if not boxes:
        return None, None
    boxes = sorted(boxes, key=lambda b: (b[2]-b[0])*(b[1]-b[3]), reverse=True)
    encs = face_recognition.face_encodings(rgb_small, [boxes[0]])
    if not encs:
        return None, None
    (t, r, b, l) = boxes[0]
    box_full = (int(t / DOWNSCALE_DETECT), int(r / DOWNSCALE_DETECT), int(b / DOWNSCALE_DETECT), int(l / DOWNSCALE_DETECT))
    return encs[0], box_full

def append_to_master(enc_list, name):
    if Path(ENCODINGS_NPY).exists():
        enc_master = np.load(ENCODINGS_NPY)
        if enc_master.ndim == 1:
            enc_master = enc_master.reshape(1, -1)
        labels = json.loads(Path(LABELS_JSON).read_text(encoding="utf-8"))
    else:
        enc_master = np.zeros((0, 128), dtype=np.float32)
        labels = []
    enc_new = np.vstack([e.astype(np.float32) for e in enc_list])
    enc_all = np.vstack([enc_master, enc_new]) if enc_master.size else enc_new
    labels += [name] * len(enc_list)
    np.save(ENCODINGS_NPY, enc_all)
    Path(LABELS_JSON).write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    return enc_all.shape[0], len(labels)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--samples', type=int, default=N_SAMPLES)
    args = parser.parse_args()

    ensure_dirs()
    name = args.name
    samples = args.samples
    print(f"Starting headless registration for: {name} ({samples} samples)")

    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("ERROR: No se pudo abrir el stream. Revisa la URL/Conectividad.")
        raise SystemExit(1)

    person_dir = os.path.join(IMAGES_DIR, name)
    os.makedirs(person_dir, exist_ok=True)

    collected = []
    sample_count = 0

    while sample_count < samples:
        got = False
        tries = 0
        while tries < MAX_TRIES_PER_SAMPLE and not got:
            tries += 1
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.2)
                continue
            enc, box = detect_largest_face_and_encode(frame)
            if enc is not None:
                collected.append(enc)
                sample_count += 1
                got = True
                filename = f"{name}_{sample_count:02d}.jpg"
                cv2.imwrite(os.path.join(person_dir, filename), frame)
                print(f"Captured sample {sample_count}/{samples}: {filename}")
            else:
                print(f"No face detected (try {tries}/{MAX_TRIES_PER_SAMPLE}), retrying...")

        if not got:
            print("Failed to capture a valid face for this sample. Exiting with failure.")
            cap.release()
            raise SystemExit(2)

    # Append encodings
    total_rows, total_labels = append_to_master(collected, name)
    print(f"Registration completed for {name}. Total entries: {total_rows}")
    cap.release()

if __name__ == '__main__':
    main()
