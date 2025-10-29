# Sistema de Reconocimiento Facial con ESP32-CAM

Sistema de reconocimiento facial en tiempo real que utiliza ESP32-CAM para captura de video y OpenCV + face_recognition para procesamiento.

## Características

- **Registro de rostros**: Captura y registra rostros de múltiples personas (archivo `register_auto.py`)
- **Reconocimiento en vivo**: Identifica personas en tiempo real desde el stream del ESP32-CAM (archivo `recolive.py`)
- **Almacenamiento persistente**: Los encodings faciales se guardan en `encodings.npy` y `labels.json`

## Requisitos

- Python 3.11+
- ESP32-CAM configurado con CameraWebServer o similar
- Cámara USB o acceso al stream del ESP32-CAM

## Estructura del Proyecto

```
.
├── register_auto.py       # Script para registrar nuevos rostros
├── recolive.py            # Script de reconocimiento en vivo
├── encodings.npy          # Base de datos de encodings faciales
├── labels.json           # Nombres asociados a los encodings
├── requirements.txt      # Dependencias de Python
├── Dockerfile           # Configuración de contenedor Docker
├── docker-compose.yml   # Orquestación de contenedores
├── deploy.sh            # Script de despliegue automatizado
├── DEPLOYMENT.md        # Guía de despliegue en EC2
└── README.md            # Este archivo
```

## Instalación Local

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd hardware_ESP32Cam
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar la URL del stream

Edita los archivos `.py` y ajusta la variable `STREAM_URL`:

```python
STREAM_URL = "http://192.168.18.30:81/stream"  # Tu IP del ESP32-CAM
```

## Uso

### Registrar nuevos rostros

```bash
python register_auto.py
```

- Presiona 'R' para registrar una persona
- Ingresa el nombre cuando se solicite
- El sistema capturará 3 muestras automáticamente
- Presiona ESC para salir

### Reconocimiento en vivo

```bash
python recolive.py
```

- El sistema mostrará una ventana con el reconocimiento en tiempo real
- Presiona ESC para salir

## Despliegue con Docker

### Construir la imagen

```bash
docker-compose build
```

### Ejecutar el contenedor

```bash
docker-compose up -d
```

### Ver logs

```bash
docker-compose logs -f
```

### Detener el contenedor

```bash
docker-compose down
```

## Despliegue en EC2

Consulta el archivo `DEPLOYMENT.md` para instrucciones detalladas.

### Despliegue rápido con script automatizado

```bash
./deploy.sh 3.16.78.139 ~/.ssh/tu-clave.pem
```

**Importante:** Edita el script `deploy.sh` y actualiza la variable `REPO_URL` con la URL de tu repositorio en GitHub.

## Configuración

### Variables importantes

En `register_auto.py` y `recolive.py`:

- `STREAM_URL`: URL del stream del ESP32-CAM
- `THRESHOLD`: Umbral de similitud para reconocimiento (0.6-0.62 recomendado)
- `N_SAMPLES`: Número de muestras por persona al registrar (por defecto: 3)
- `DOWNSCALE`: Factor de reducción de resolución para acelerar procesamiento

### Hardware ESP32-CAM

Asegúrate de que tu ESP32-CAM esté configurado con:
- CameraWebServer o firmware similar
- Stream HTTP accesible en tu red local
- Flash LED funcional (opcional, para iluminación durante captura)

## Solución de Problemas

### Error: "No se pudo abrir el stream"

- Verifica que la IP del ESP32-CAM sea correcta
- Asegúrate de que el ESP32-CAM esté en la misma red
- Prueba la URL en un navegador web

### Error: "No module named 'cv2'"

```bash
pip install opencv-python
```

### Reconocimiento impreciso

- Captura más muestras por persona (aumenta `N_SAMPLES`)
- Asegura buena iluminación durante el registro
- Ajusta el umbral `THRESHOLD`

## Notas

- La aplicación usa OpenCV para mostrar ventanas. En entornos sin GUI (como servidores), tendrás que modificar el código para guardar frames como imágenes en lugar de usar `cv2.imshow()`.
- Los datos de reconocimiento se guardan localmente en `encodings.npy` y `labels.json`.
- El directorio `capturas_registro/` almacena las imágenes capturadas durante el registro (si `SAVE_IMAGES = True`).

## Licencia

Este proyecto es de código abierto.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request.

