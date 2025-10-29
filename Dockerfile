# Usar imagen base de Python con soporte para OpenCV
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para OpenCV y face_recognition
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar archivos de la aplicación
COPY *.py ./
COPY *.npy ./
COPY *.json ./

# Crear directorios necesarios
RUN mkdir -p capturas_registro captured_frames recognition_results

# Exponer puerto de la API Flask
EXPOSE 5000

# Comando por defecto - correr API Flask
CMD ["python", "app.py"]

