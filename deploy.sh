#!/bin/bash

# Script de despliegue automatizado para EC2
# Uso: ./deploy.sh <IP_EC2> <RUTA_CLAVE_SSH>

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar argumentos
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}Uso: $0 <IP_EC2> <RUTA_CLAVE_SSH>${NC}"
    echo "Ejemplo: $0 3.16.78.139 ~/.ssh/my-key.pem"
    exit 1
fi

EC2_IP=$1
SSH_KEY=$2
USER="ec2-user"  # Cambiar si usas otro usuario

echo -e "${BLUE}🚀 Iniciando despliegue a EC2 ($EC2_IP)${NC}"

# Verificar que existe la clave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ No se encuentra la clave SSH: $SSH_KEY${NC}"
    exit 1
fi

# 1. Verificar Docker en la instancia
echo -e "${BLUE}📦 Verificando Docker en la instancia...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $USER@$EC2_IP << 'EOF'
    if ! command -v docker &> /dev/null; then
        echo "Instalando Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        echo "Docker instalado. Por favor reconéctate."
        exit 0
    fi
    echo "✓ Docker ya está instalado"
EOF

# 2. Clonar/actualizar el repositorio
echo -e "${BLUE}📥 Clonando/actualizando repositorio...${NC}"
REPO_URL="https://github.com/aaiquipameza-del/hardware_ESP32Cam.git"  # CAMBIAR ESTA URL

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $USER@$EC2_IP << EOF
    if [ -d "hardware_ESP32Cam" ]; then
        cd hardware_ESP32Cam
        git pull
    else
        git clone $REPO_URL hardware_ESP32Cam
        cd hardware_ESP32Cam
    fi
EOF

# 3. Copiar archivos necesarios
echo -e "${BLUE}📤 Copiando archivos al servidor...${NC}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    Dockerfile docker-compose.yml requirements.txt .dockerignore \
    register_auto.py recolive.py encodings.npy labels.json \
    $USER@$EC2_IP:~/hardware_ESP32Cam/

# 4. Crear archivo .env si no existe
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $USER@$EC2_IP << 'EOF'
    cd hardware_ESP32Cam
    if [ ! -f .env ]; then
        echo "STREAM_URL=http://192.168.18.30:81/stream" > .env
        echo "✓ Archivo .env creado"
    fi
EOF

# 5. Construir y ejecutar
echo -e "${BLUE}🔨 Construyendo imagen Docker...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $USER@$EC2_IP << 'EOF'
    cd hardware_ESP32Cam
    docker-compose down
    docker-compose build --no-cache
    echo "✓ Imagen construida"
EOF

echo -e "${BLUE}🚀 Iniciando contenedores...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=quiet $USER@$EC2_IP << 'EOF'
    cd hardware_ESP32Cam
    docker-compose up -d
    echo "✓ Contenedor iniciado"
EOF

# 6. Verificar estado
echo -e "${BLUE}📊 Verificando estado del despliegue...${NC}"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no $USER@$EC2_IP << 'EOF'
    cd hardware_ESP32Cam
    docker-compose ps
    echo ""
    echo "Últimas líneas de logs:"
    docker-compose logs --tail=20
EOF

echo -e "${GREEN}✅ Despliegue completado exitosamente${NC}"
echo -e "${BLUE}Para ver los logs: ssh -i $SSH_KEY $USER@$EC2_IP 'cd hardware_ESP32Cam && docker-compose logs -f'${NC}"

