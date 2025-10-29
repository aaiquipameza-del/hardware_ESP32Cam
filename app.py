# app.py - API Flask para reconocimiento facial
from flask import Flask, jsonify, request
from flask_cors import CORS
import cv2
import json
import time
import threading
import numpy as np
import face_recognition
from pathlib import Path
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# Configuración
ENCODINGS_NPY = "encodings.npy"
LABELS_JSON = "labels.json"
THRESHOLD = 0.6
DOWNSCALE = 0.5
FRAMES_DIR = "captured_frames"
RESULTS_DIR = "recognition_results"

# Estado global
recognition_active = False
stream_url = os.getenv("STREAM_URL", "0")  # 0 = webcam local, o cambiar por URL de ESP32
last_recognitions = []
current_frame = None
recognition_thread = None

# Crear directorios
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

def load_encodings():
    """Cargar encodings faciales desde archivos"""
    if not Path(ENCODINGS_NPY).exists() or not Path(LABELS_JSON).exists():
        return None, None
    
    encs = np.load(ENCODINGS_NPY)
    with open(LABELS_JSON, "r", encoding="utf-8") as f:
        labels = json.load(f)
    
    if encs.dtype != np.float32:
        encs = encs.astype(np.float32)
    
    return encs, labels

def best_match(unknown_enc: np.ndarray, known_encs: np.ndarray, labels: list, thr=THRESHOLD):
    """Encontrar la mejor coincidencia"""
    dists = np.linalg.norm(known_encs - unknown_enc.astype(np.float32), axis=1)
    idx = int(np.argmin(dists))
    name = labels[idx]
    dist = float(dists[idx])
    if dist <= thr:
        return name, dist
    return "Desconocido", dist

def recognition_loop():
    """Loop principal de reconocimiento"""
    global recognition_active, last_recognitions, current_frame
    
    known_encs, labels = load_encodings()
    if known_encs is None:
        print("❌ No se encontraron encodings. Registra personas primero.")
        return
    
    print(f"✅ Encodings cargados: {len(labels)} personas")
    
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"❌ No se pudo abrir el stream: {stream_url}")
        return
    
    print(f"✅ Conectado al stream: {stream_url}")
    
    frame_count = 0
    
    while recognition_active:
        ok, frame = cap.read()
        if not ok:
            time.sleep(1)
            continue
        
        frame_count += 1
        current_frame = frame.copy()
        
        # Procesar cada AVA Frame para acelerar
        if frame_count % 3 != 0:
            continue
        
        # Redimensionar para acelerar
        small = cv2.resize(frame, (0, 0), fx=DOWNSCALE, fy=DOWNSCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        
        # Detectar y encodear
        boxes = face_recognition.face_locations(rgb_small, model="hog")
        encs = face_recognition.face_encodings(rgb_small, boxes)
        
        # Procesar detecciones
        for i, (enc, (t, r, b, l)) in enumerate(zip(encs, boxes)):
            name, dist = best_match(enc, known_encs, labels, THRESHOLD)
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "name": name,
                "confidence": round(1 - dist, 2),
                "distance": round(dist, 3),
                "box": {
                    "top": int(t / DOWNSCALE),
                    "right": int(r / DOWNSCALE),
                    "bottom": int(b / DOWNSCALE),
                    "left": int(l / DOWNSCALE)
                }
            }
            
            # Guardar en lista de resultados
            last_recognitions.append(result)
            if len(last_recognitions) > 50:  # Mantener solo últimos 50
                last_recognitions.pop(0)
            
            print(f"👤 Reconocido: {name} (confianza: {result['confidence']:.2f})")
            
            # Guardar frame si es reconocido
            if name != "Desconocido":
                filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.jpg"
                filepath = os.path.join(FRAMES_DIR, filename)
                cv2.imwrite(filepath, frame)
                
                # Guardar resultado en JSON
                result_file = os.path.join(RESULTS_DIR, f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
    
    cap.release()
    print("🛑 Reconocimiento detenido")

@app.route('/')
def index():
    """Página principal"""
    return jsonify({
        "message": "API de Reconocimiento Facial ESP32-CAM",
        "version": "1.0",
        "endpoints": {
            "/api/start": "POST - Iniciar reconocimiento",
            "/api/stop": "POST - Detener reconocimiento",
            "/api/status": "GET - Estado actual",
            "/api/results": "GET - Últimos resultados",
            "/api/latest": "GET - Último resultado",
            "/api/stats": "GET - Estadísticas",
            "/api/register": "POST - Registrar persona (JSON con 'name' y 'encodings')",
            "/api/config": "PUT - Cambiar configuración"
        }
    })

@app.route('/api/start', methods=['POST'])
def start_recognition():
    """Iniciar reconocimiento facial"""
    global recognition_active, recognition_thread
    
    if recognition_active:
        return jsonify({"error": "El reconocimiento ya está activo"}), 400
    
    recognition_active = True
    recognition_thread = threading.Thread(target=recognition_loop, daemon=True)
    recognition_thread.start()
    
    return jsonify({
        "status": "started",
        "message": "Reconocimiento facial iniciado",
        "stream_url": stream_url
    })

@app.route('/api/stop', methods=['POST'])
def stop_recognition():
    """Detener reconocimiento facial"""
    global recognition_active
    
    recognition_active = False
    return jsonify({
        "status": "stopped",
        "message": "Reconocimiento facial detenido"
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """Obtener estado actual"""
    return jsonify({
        "active": recognition_active,
        "stream_url": stream_url,
        "total_results": len(last_recognitions),
        "encodings_loaded": Path(ENCODINGS_NPY).exists()
    })

@app.route('/api/results', methods=['GET'])
def get_results():
    """Obtener últimos resultados"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        "results": last_recognitions[-limit:],
        "total": len(last_recognitions)
    })

@app.route('/api/latest', methods=['GET'])
def get_latest():
    """Obtener último resultado"""
    if not last_recognitions:
        return jsonify({"error": "No hay resultados disponibles"}), 404
    
    return jsonify(last_recognitions[-1])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Obtener estadísticas de reconocimiento"""
    if not last_recognitions:
        return jsonify({
            "total_detections": 0,
            "recognized": {},
            "unknown_count": 0
        })
    
    recognized = {}
    unknown_count = 0
    
    for result in last_recognitions:
        if result["name"] == "Desconocido":
            unknown_count += 1
        else:
            if result["name"] not in recognized:
                recognized[result["name"]] = 0
            recognized[result["name"]] += 1
    
    return jsonify({
        "total_detections": len(last_recognitions),
        "recognized": recognized,
        "unknown_count": unknown_count,
        "unique_persons": len(recognized)
    })

@app.route('/api/config', methods=['PUT'])
def update_config():
    """Actualizar configuración"""
    global stream_url, THRESHOLD
    
    data = request.json
    if 'stream_url' in data:
        if recognition_active:
            return jsonify({"error": "Detén el reconocimiento antes de cambiar la URL"}), 400
        stream_url = data['stream_url']
        os.environ['STREAM_URL'] = stream_url
    
    if 'threshold' in data:
        THRESHOLD = data['threshold']
    
    return jsonify({
        "stream_url": stream_url,
        "threshold": THRESHOLD
    })

@app.route('/api/register', methods=['POST'])
def register_person():
    """Registrar una nueva persona"""
    # Esta función requiere implementación adicional
    # Por ahora, usar register_auto.py manualmente
    return jsonify({
        "message": "Usa el script register_auto.py para registrar personas",
        "instructions": "Ejecuta: python register_auto.py"
    })

def add_seed_results():
    """Agregar 5 resultados de prueba al inicio"""
    global last_recognitions
    
    # Obtener usuarios únicos de labels.json
    if Path(LABELS_JSON).exists():
        with open(LABELS_JSON, 'r', encoding='utf-8') as f:
            all_labels = json.load(f)
        unique_users = list(set(all_labels))
    else:
        unique_users = ["sharon", "taylor"]
    
    # Crear 5 resultados de prueba con usuarios existentes
    base_time = datetime.now()
    seed_results = []
    
    for i in range(5):
        # Alternar entre los usuarios disponibles
        user = unique_users[i % len(unique_users)]
        confidence = round(0.75 + (i * 0.04), 2)  # Variar confianza entre 0.75 y 0.91
        
        result = {
            "timestamp": (base_time - timedelta(seconds=(5-i)*30)).isoformat(),
            "name": user,
            "confidence": confidence,
            "distance": round(1 - confidence, 3),
            "box": {
                "top": 100 + i * 20,
                "right": 200 + i * 15,
                "bottom": 300 + i * 20,
                "left": 150 + i * 15
            }
        }
        seed_results.append(result)
    
    last_recognitions.extend(seed_results)
    print(f"🌱 {len(seed_results)} resultados de prueba agregados")

if __name__ == '__main__':
    print("🚀 Iniciando API de Reconocimiento Facial")
    print("📡 Stream URL:", stream_url)
    print("📝 Cargando encodings...")
    
    if Path(ENCODINGS_NPY).exists():
        encs, labels = load_encodings()
        print(f"✅ {len(labels)} encodings cargados")
        # Agregar resultados de prueba basados en los usuarios registrados
        add_seed_results()
    else:
        print("⚠️ No se encontraron encodings. Registra personas primero con register_auto.py")
    
    app.run(host='0.0.0.0', port=5001, debug=False)

