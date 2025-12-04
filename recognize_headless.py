#!/usr/bin/env python3
"""
Recognize a face from an image (base64) against stored encodings.
Uses face_recognition library. Returns JSON with result.
"""
import sys
import json
import base64
import numpy as np
from pathlib import Path
from io import BytesIO
import cv2

# Try importing face_recognition; if not available, show helpful error
try:
    import face_recognition
except ImportError as e:
    print(json.dumps({
        "ok": False,
        "message": f"face_recognition not installed: {str(e)}. Install with: pip install face-recognition",
        "recognized": False
    }))
    sys.exit(1)

ENCODINGS_NPY = "encodings.npy"
LABELS_JSON = "labels.json"
THRESHOLD = 0.6

def load_encodings():
    if not Path(ENCODINGS_NPY).exists() or not Path(LABELS_JSON).exists():
        return None, None
    
    encs = np.load(ENCODINGS_NPY)
    if encs.ndim == 1:
        encs = encs.reshape(1, -1)
    
    with open(LABELS_JSON, "r", encoding="utf-8") as f:
        labels = json.load(f)
    
    if encs.dtype != np.float32:
        encs = encs.astype(np.float32)
    
    if len(encs) != len(labels):
        return None, None
    
    return encs, labels

def best_match(unknown_enc: np.ndarray, known_encs: np.ndarray, labels: list, thr=THRESHOLD):
    """Return (name, distance) or (None, 1.0) if no match."""
    if len(known_encs) == 0:
        return None, 1.0
    dists = np.linalg.norm(known_encs - unknown_enc.astype(np.float32), axis=1)
    idx = int(np.argmin(dists))
    name = labels[idx]
    dist = float(dists[idx])
    if dist <= thr:
        return name, dist
    return None, dist

def recognize_from_base64(image_base64: str):
    """Decode base64 image and recognize face."""
    try:
        # Decode base64
        img_data = base64.b64decode(image_base64.split(',')[1] if ',' in image_base64 else image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"ok": False, "message": "Could not decode image", "recognized": False}
        
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        boxes = face_recognition.face_locations(img_rgb, model="hog")
        if not boxes:
            return {"ok": False, "message": "No face detected", "recognized": False}
        
        # Encode the largest face
        encs = face_recognition.face_encodings(img_rgb, boxes)
        if not encs:
            return {"ok": False, "message": "Could not encode face", "recognized": False}
        
        # Load known encodings
        known_encs, labels = load_encodings()
        if known_encs is None:
            return {"ok": False, "message": "No encodings loaded", "recognized": False}
        
        # Match
        name, distance = best_match(encs[0], known_encs, labels, THRESHOLD)
        
        if name:
            return {
                "ok": True,
                "recognized": True,
                "clientName": name,
                "confidence": float(1.0 - distance),
                "distance": distance
            }
        else:
            return {
                "ok": True,
                "recognized": False,
                "message": "Face not recognized",
                "distance": distance
            }
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "message": f"Error: {str(e)}",
            "recognized": False,
            "traceback": traceback.format_exc()
        }

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "message": "Usage: recognize_headless.py <base64_image>", "recognized": False}))
        sys.exit(1)
    
    image_base64 = sys.argv[1]
    result = recognize_from_base64(image_base64)
    print(json.dumps(result))
