# Guía Rápida de Despliegue

## Pasos para Desplegar en EC2

### Opción 1: Despliegue Automatizado (Recomendado)

1. **Edita `deploy.sh`** y actualiza la URL del repositorio:
   ```bash
   REPO_URL="https://github.com/TU-USUARIO/TU-REPO.git"
   ```

2. **Ejecuta el script de despliegue:**
   ```bash
   ./deploy.sh 3.16.78.139 /ruta/a/tu/clave.pem
   ```

### Opción 2: Despliegue Manual

1. **Conéctate a la instancia EC2:**
   ```bash
   ssh -i /ruta/a/tu/clave.pem ubuntu@3.16.78.139
   ```

2. **Instala Docker (si no está instalado):**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   exit  # Cierra y reconéctate para aplicar cambios
   ```

3. **Clona el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd hardware_ESP32Cam
   ```

4. **Configura el archivo .env:**
   ```bash
   echo "STREAM_URL=http://192.168.18.30:81/stream" > .env
   ```

5. **Construye y ejecuta:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

6. **Verifica los logs:**
   ```bash
   docker-compose logs -f
   ```

## Comandos Útiles

### Ver estado del contenedor
```bash
docker-compose ps
```

### Ver logs en tiempo real
```bash
docker-compose logs -f
```

### Detener la aplicación
```bash
docker-compose down
```

### Reiniciar después de cambios
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Acceder al contenedor
```bash
docker-compose exec face-recognition bash
```

## Configuración de Red

Si tu ESP32-CAM está en una red local diferente:

### Opción A: Túnel SSH
```bash
ssh -i /ruta/a/tu/clave.pem -L 8081:192.168.18.30:81 ubuntu@3.16.78.139 -N
```
Luego usa `STREAM_URL=http://localhost:8081/stream`

### Opción B: VPN entre las redes

## Importante: Interfaz Gráfica

Este proyecto usa `cv2.imshow()` que requiere GUI. En EC2 sin display:

### Modificación Opcional: Sin GUI

Si necesitas operar sin GUI, puedes modificar los scripts para:
1. Guardar frames como archivos JPEG
2. Mostrar resultados en la consola/logs
3. Usar Flask/FastAPI para crear una API REST

¿Quieres que cree una versión sin GUI del código?

## Verificar el Estado

```bash
# Ver procesos en ejecución
docker ps

# Ver logs del contenedor
docker logs esp32cam-recognition

# Ver uso de recursos
docker stats
```

## Backup de Datos

```bash
# En EC2
cd hardware_ESP32Cam
tar -czf backup-$(date +%Y%m%d).tar.gz encodings.npy labels.json capturas_registro/

# Descargar a tu máquina local
scp -i /ruta/a/tu/clave.pem ubuntu@3.16.78.139:~/hardware_ESP32Cam/backup-*.tar.gz ./
```

## Actualizar el Código

```bash
# En EC2
cd hardware_ESP32Cam
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

## Solución de Problemas

### Error: "Cannot connect to the Docker daemon"
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Error: "No module named"
```bash
docker-compose build --no-cache
docker-compose up -d
```

### El contenedor se detiene inmediatamente
```bash
docker-compose logs  # Ver logs para diagnóstico
```

## Contacto

Para más detalles, consulta `DEPLOYMENT.md` y `README.md`.



