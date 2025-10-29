# Documentación de la API de Reconocimiento Facial

## Endpoints Disponibles

### 1. GET `/`
Información general sobre la API

**Respuesta:**
```json
{
  "message": "API de Reconocimiento Facial ESP32-CAM",
  "version": "1.0",
  "endpoints": { ... }
}
```

---

### 2. POST `/api/start`
Inicia el reconocimiento facial

**Request:**
```bash
curl -X POST http://3.16.78.139:5000/api/start
```

**Respuesta:**
```json
{
  "status": "started",
  "message": "Reconocimiento facial iniciado",
  "stream_url": "http://192.168.18.30:81/stream"
}
```

---

### 3. POST `/api/stop`
Detiene el reconocimiento facial

**Request:**
```bash
curl -X POST http://3.16.78.139:5000/api/stop
```

**Respuesta:**
```json
{
  "status": "stopped",
  "message": "Reconocimiento facial detenido"
}
```

---

### 4. GET `/api/status`
Obtiene el estado actual del sistema

**Request:**
```bash
curl http://3.16.78.139:5000/api/status
```

**Respuesta:**
```json
{
  "active": true,
  "stream_url": "http://192.168.18.30:81/stream",
  "total_results": 15,
  "encodings_loaded": true
}
```

---

### 5. GET `/api/results`
Obtiene los últimos resultados de reconocimiento

**Request:**
```bash
curl http://3.16.78.139:5000/api/results?limit=10
```

**Parámetros:**
- `limit` (opcional): Número de resultados a retornar (default: 20)

**Respuesta:**
```json
{
  "results": [
    {
      "timestamp": "2025-10-29T00:15:30.123456",
      "name": "Juan",
      "confidence": 0.87 DEFAULT,
      "distance": 0.13,
      "box": {
        "top": 150,
        "right": 400,
        "bottom": 350,
        "left": 200
      }
    }
  ],
  "total": 15
}
```

---

### 6. GET `/api/latest`
Obtiene el último resultado de reconocimiento

**Request:**
```bash
curl http://3.16.78.139:5000/api/latest
```

**Respuesta:**
```json
{
  "timestamp": "2025-10-29T00:15:30.123456",
  "name": "Juan",
  "confidence": 0.87,
  "distance": 0.13,
  "box": {
    "top": 150,
    "right": 400,
    "bottom": 350,
    "left": 200
  }
}
```

---

### 7. GET `/api/stats`
Obtiene estadísticas de reconocimiento

**Request:**
```bash
curl http://3.16.78.139:5000/api/stats
```

**Respuesta:**
```json
{
  "total_detections": 45,
  "recognized": {
    "Juan": 20,
    "María": 15
  },
  "unknown_count": 10,
  "unique_persons": 2
}
```

---

### 8. PUT `/api/config`
Actualiza la configuración

**Request:**
```bash
curl -X PUT http://3.16.78.139:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "stream_url": "http://192.168.1.100:81/stream",
    "threshold": 0.62
  }'
```

**Body:**
```json
{
  "stream_url": "http://nueva-ip:81/stream",
  "threshold": 0.62
}
```

**Respuesta:**
```json
{
  "stream_url": "http://nueva-ip:81/stream",
  "threshold": 0.62
}
```

---

### 9. POST `/api/register`
Registrar nueva persona (Por implementar)

**Request:**
```bash
curl -X POST http://3.16.78.139:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"name": "NuevaPersona"}'
```

---

## Ejemplos de Uso

### Flujo completo de reconocimiento

```bash
# 1. Iniciar reconocimiento
curl -X POST http://3.16.78.139:5000/api/start

# 2. Verificar estado
curl http://3.16.78.139:5000/api/status

# 3. Obtener últimos resultados
curl http://3.16.78.139:5000/api/results

# 4. Ver estadísticas
curl http://3.16.78.139:5000/api/stats

# 5. Detener reconocimiento
curl -X POST http://3.16.78.139:5000/api/stop
```

### Con Python

```python
import requests

BASE_URL = "http://3.16.78.139:5000"

# Iniciar reconocimiento
response = requests.post(f"{BASE_URL}/api/start")
print(response.json())

# Obtener resultados
response = requests.get(f"{BASE_URL}/api/results?limit=5")
results = response.json()
for result in results["results"]:
    print(f"{result['name']}: {result['confidence']:.2f}")

# Ver estadísticas
response = requests.get(f"{BASE_URL}/api/stats")
stats = response.json()
print(f"Total detecciones: {stats['total_detections']}")
```

### Con JavaScript/Fetch

```javascript
const BASE_URL = 'http://3.16.78.139:5000';

// Iniciar reconocimiento
fetch(`${BASE_URL}/api/start`, { method: 'POST' })
  .then(r => r.json())
  .then(data => console.log(data));

// Obtener últimos resultados
fetch(`${BASE_URL}/api/results?limit=10`)
  .then(r => r.json())
  .then(data => {
    data.results.forEach(result => {
      console.log(`${result.name}: ${result.confidence}`);
    });
  });

// Obtener estadísticas
fetch(`${BASE_URL}/api/stats`)
  .then(r => r.json())
  .then(stats => console.log(stats));
```

---

## Variables de Entorno

- `STREAM_URL`: URL del stream del ESP32-CAM (default: `http://192.168.18.30:81/stream`)

## Archivos Generados

El sistema genera automáticamente:

1. **Frames capturados**: `captured_frames/` - Imágenes de personas reconocidas
2. **Resultados JSON**: `recognition_results/` - Metadatos de cada reconocimiento
3. **Logs de consola**: Información en tiempo real del reconocimiento

## Notas

- El reconocimiento debe estar activo (`/api/start`) para que se generen resultados
- Los frames se guardan automáticamente cuando se reconoce a una persona
- Se mantienen los últimos 50 resultados en memoria
- El umbral de reconocimiento por defecto es 0.6 (configurable)

