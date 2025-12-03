#!/bin/bash
# Script para arreglar el build de Docker que se queda atascado en dlib

echo "🛑 Deteniendo cualquier build en progreso..."
ssh -i "proy1-key.pem" -o StrictHostKeyChecking=no ubuntu@ec2-3-16-162-219.us-east-2.compute.amazonaws.com << 'EOF'
    cd ~/hardware_ESP32Cam
    
    # Detener cualquier contenedor en ejecución
    sudo docker compose down 2>/dev/null || true
    
    # Detener cualquier build en progreso (si hay)
    sudo docker ps -a | grep -i build | awk '{print $1}' | xargs -r sudo docker stop 2>/dev/null || true
    
    # Limpiar builds incompletos
    sudo docker builder prune -f
    
    echo "✅ Builds detenidos"
EOF

echo "📤 Copiando Dockerfile actualizado..."
scp -i "proy1-key.pem" -o StrictHostKeyChecking=no Dockerfile ubuntu@ec2-3-16-162-219.us-east-2.compute.amazonaws.com:~/hardware_ESP32Cam/

echo "🔨 Reconstruyendo con el Dockerfile optimizado..."
ssh -i "proy1-key.pem" -o StrictHostKeyChecking=no ubuntu@ec2-3-16-162-219.us-east-2.compute.amazonaws.com << 'EOF'
    cd ~/hardware_ESP32Cam
    
    echo "Construyendo imagen (esto puede tardar unos minutos pero NO debería quedarse atascado)..."
    sudo docker compose build --no-cache --progress=plain 2>&1 | tee build.log
    
    if [ $? -eq 0 ]; then
        echo "✅ Build completado exitosamente!"
        echo "🚀 Iniciando contenedor..."
        sudo docker compose up -d
        echo "📊 Estado del contenedor:"
        sudo docker compose ps
        echo "📋 Últimas líneas de logs:"
        sudo docker compose logs --tail=20
    else
        echo "❌ Error en el build. Revisa build.log para más detalles."
    fi
EOF

echo "✅ Proceso completado!"


