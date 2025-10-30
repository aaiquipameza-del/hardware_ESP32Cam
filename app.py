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
    """Página principal con HTML"""
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Reconocimiento Facial</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
            
            .subtitle {
                color: rgba(255,255,255,0.9);
                text-align: center;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            
            .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            }
            
            .card:hover {
                transform: translateY(-5px);
            }
            
            .card h2 {
                color: #667eea;
                margin-bottom: 15px;
                font-size: 1.5em;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .card h2::before {
                content: '🎯';
                font-size: 1.2em;
            }
            
            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 0.9em;
                margin: 10px 0;
            }
            
            .status-active {
                background: #4CAF50;
                color: white;
            }
            
            .status-inactive {
                background: #f44336;
                color: white;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }
            
            .stat-item {
                background: #f5f5f5;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
                display: block;
            }
            
            .stat-label {
                color: #666;
                font-size: 0.9em;
                margin-top: 5px;
            }
            
            .controls {
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                margin-bottom: 30px;
            }
            
            button {
                flex: 1;
                min-width: 200px;
                padding: 15px 30px;
                border: none;
                border-radius: 10px;
                font-size: 1.1em;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                color: white;
            }
            
            .btn-start {
                background: linear-gradient(135deg, #4CAF50, #45a049);
            }
            
            .btn-start:hover {
                background: linear-gradient(135deg, #45a049, #3d8b40);
                transform: scale(1.05);
            }
            
            .btn-stop {
                background: linear-gradient(135deg, #f44336, #da190b);
            }
            
            .btn-stop:hover {
                background: linear-gradient(135deg, #da190b, #c62828);
                transform: scale(1.05);
            }
            
            .btn-refresh {
                background: linear-gradient(135deg, #2196F3, #0b7dda);
            }
            
            .btn-refresh:hover {
                background: linear-gradient(135deg, #0b7dda, #1976D2);
                transform: scale(1.05);
            }
            
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none !important;
            }
            
            .endpoints {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            
            .endpoints h2 {
                color: #667eea;
                margin-bottom: 20px;
                font-size: 1.8em;
            }
            
            .endpoint-item {
                padding: 15px;
                background: #f9f9f9;
                border-left: 4px solid #667eea;
                margin-bottom: 10px;
                border-radius: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .method {
                display: inline-block;
                padding: 5px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }
            
            .method-get { background: #2196F3; color: white; }
            .method-post { background: #4CAF50; color: white; }
            .method-put { background: #FF9800; color: white; }
            
            .loading {
                text-align: center;
                color: white;
                font-size: 1.2em;
                padding: 20px;
            }
            
            .error {
                background: #ffebee;
                color: #c62828;
                padding: 15px;
                border-radius: 10px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎭 Face Recognition API</h1>
            <p class="subtitle">Sistema de Reconocimiento Facial con ESP32-CAM</p>
            
            <div class="controls">
                <button class="btn-start" id="btnStart">▶️ Iniciar Reconocimiento</button>
                <button class="btn-stop" id="btnStop" disabled>⏹️ Detener Reconocimiento</button>
                <button class="btn-refresh" id="btnRefresh">🔄 Actualizar Datos</button>
            </div>
            
            <div class="loading" id="loading">Cargando datos...</div>
            
            <div class="dashboard" id="dashboard" style="display: none;">
                <div class="card">
                    <h2>Estado del Sistema</h2>
                    <div id="statusContent">Cargando...</div>
                </div>
                
                <div class="card">
                    <h2>📊 Estadísticas</h2>
                    <div class="stats-grid" id="statsContent">
                        <div class="stat-item">
                            <span class="stat-value" id="totalDetections">0</span>
                            <span class="stat-label">Detecciones Totales</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="uniquePersons">0</span>
                            <span class="stat-label">Personas Únicas</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="unknownCount">0</span>
                            <span class="stat-label">Desconocidos</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="totalResults">0</span>
                            <span class="stat-label">Total Resultados</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="endpoints">
                <h2>📡 Endpoints de la API</h2>
                <div class="endpoint-item">
                    <span><span class="method method-get">GET</span> <strong>/api/status</strong> - Estado actual</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-post">POST</span> <strong>/api/start</strong> - Iniciar reconocimiento</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-post">POST</span> <strong>/api/stop</strong> - Detener reconocimiento</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-get">GET</span> <strong>/api/results</strong> - Últimos resultados</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-get">GET</span> <strong>/api/results/&lt;name&gt;</strong> - Resultados por usuario</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-get">GET</span> <strong>/api/latest</strong> - Último resultado</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-get">GET</span> <strong>/api/stats</strong> - Estadísticas</span>
                </div>
                <div class="endpoint-item">
                    <span><span class="method method-put">PUT</span> <strong>/api/config</strong> - Cambiar configuración</span>
                </div>
            </div>
        </div>
        
        <script>
            const API_URL = window.location.origin + '/api';
            
            async function fetchData() {
                try {
                    const [statusRes, statsRes] = await Promise.all([
                        fetch(API_URL + '/status'),
                        fetch(API_URL + '/stats')
                    ]);
                    
                    const status = await statusRes.json();
                    const stats = await statsRes.json();
                    
                    // Mostrar dashboard
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'grid';
                    
                    // Actualizar estado
                    const statusHtml = `
                        <div class="status-badge ${status.active ? 'status-active' : 'status-inactive'}">
                            ${status.active ? '🔴 ACTIVO' : '⚪ INACTIVO'}
                        </div>
                        <p><strong>Stream:</strong> ${status.stream_url}</p>
                        <p><strong>Encodings:</strong> ${status.encodings_loaded ? '✅ Cargados' : '❌ No cargados'}</p>
                        <p><strong>Total Resultados:</strong> ${status.total_results}</p>
                    `;
                    document.getElementById('statusContent').innerHTML = statusHtml;
                    
                    // Actualizar estadísticas
                    document.getElementById('totalDetections').textContent = stats.total_detections || 0;
                    document.getElementById('uniquePersons').textContent = stats.unique_persons || 0;
                    document.getElementById('unknownCount').textContent = stats.unknown_count || 0;
                    document.getElementById('totalResults').textContent = status.total_results || 0;
                    
                    // Actualizar botones
                    document.getElementById('btnStart').disabled = status.active;
                    document.getElementById('btnStop').disabled = !status.active;
                    
                } catch (error) {
                    document.getElementById('loading').innerHTML = '<div class="error">❌ Error al cargar datos: ' + error.message + '</div>';
                }
            }
            
            document.getElementById('btnStart').addEventListener('click', async () => {
                try {
                    const response = await fetch(API_URL + '/start', { method: 'POST' });
                    const data = await response.json();
                    alert('✅ ' + data.message);
                    fetchData();
                } catch (error) {
                    alert('❌ Error: ' + error.message);
                }
            });
            
            document.getElementById('btnStop').addEventListener('click', async () => {
                try {
                    const response = await fetch(API_URL + '/stop', { method: 'POST' });
                    const data = await response.json();
                    alert('🛑 ' + data.message);
                    fetchData();
                } catch (error) {
                    alert('❌ Error: ' + error.message);
                }
            });
            
            document.getElementById('btnRefresh').addEventListener('click', () => {
                fetchData();
            });
            
            // Cargar datos iniciales
            fetchData();
            
            // Actualizar cada 5 segundos
            setInterval(fetchData, 5000);
        </script>
    </body>
    </html>
    """
    return html

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

@app.route('/api/results/<name>', methods=['GET'])
def get_results_by_name(name):
    """Obtener resultados filtrados por nombre de usuario"""
    limit = request.args.get('limit', 20, type=int)
    
    # Filtrar resultados por nombre
    filtered_results = [r for r in last_recognitions if r.get("name", "").lower() == name.lower()]
    
    # Aplicar límite
    limited_results = filtered_results[-limit:] if len(filtered_results) > limit else filtered_results
    
    return jsonify({
        "user": name,
        "results": limited_results,
        "total": len(filtered_results),
        "returned": len(limited_results)
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

