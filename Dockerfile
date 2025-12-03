# Usar imagen base de Python con soporte para OpenCV (3.9 tiene mejor soporte para dlib-bin)
FROM python:3.9-slim

# Instalar dependencias del sistema necesarias para OpenCV y face_recognition
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos e instalar dependencias de Python
COPY requirements.txt .

# Configurar pip para preferir paquetes binarios
ENV PIP_PREFER_BINARY=1

# Instalar numpy primero (requerido por dlib)
RUN pip install --no-cache-dir --prefer-binary numpy==1.24.3

# Instalar dlib-bin explícitamente primero para evitar compilación desde fuente
RUN pip install --no-cache-dir --prefer-binary dlib-bin==19.24.6

# Instalar el resto de dependencias (face-recognition detectará que dlib ya está instalado)
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

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

