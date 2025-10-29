# Guía de Despliegue en EC2

Esta guía describe cómo desplegar la aplicación de reconocimiento facial en una instancia EC2 usando Docker.

## Requisitos Previos

1. Instancia EC2 con acceso SSH (IP: 3.16.78.139)
2. Clave privada SSH para acceder a la instancia
3. Git instalado en la máquina local
4. Repositorio pushado a GitHub

## Paso 1: Conectarse a la Instancia EC2

```bash
ssh -i /ruta/a/tu/clave.pem ubuntu@3.16.78.139
```

(Nota: Ajusta el usuario según tu AMI - puede ser `ec2-user`, `ubuntu`, etc.)

## Paso 2: Instalar Docker en EC2

```bash
# Actualizar el sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar el usuario actual al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt-get install -y docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

**Importante:** Cierra la sesión SSH y reconéctate para que los cambios de grupo tengan efecto:

```bash
exit
ssh -i /ruta/a/tu/clave.pem ubuntu@3.16.78.139
```

## Paso 3: Clonar el Repositorio

```bash
# Instalar Git si no está instalado
sudo apt-get install -y git

# Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd hardware_ESP32Cam
```

## Paso 4: Configurar Variables de Entorno

Crea un archivo `.env` para configurar las variables:

```bash
echo "STREAM_URL=http://192.168.18.30:81/stream" > .env
```

(Nota: Ajusta la URL del stream según tu configuración de ESP32-CAM)

## Paso 5: Construir y Ejecutar con Docker Compose

```bash
# Construir la imagen
docker-compose build

# Ejecutar el contenedor
docker-compose up -d

# Ver los logs
docker-compose logs -f
```

## Paso 6: Verificar que Está Funcionando

```bash
# Ver contenedores en ejecución
docker-compose ps

# Ver logs del contenedor
docker-compose logs

# Ejecutar comandos en el contenedor
docker-compose exec face-recognition bash
```

## Comandos Útiles

### Detener la aplicación:
```bash
docker-compose down
```

### Reiniciar la aplicación:
```bash
docker-compose restart
```

### Reconstruir después de cambios:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Ver uso de recursos:
```bash
docker stats
```

### Acceder al contenedor en ejecución:
```bash
docker-compose exec face-recognition bash
```

## Configuración de Red

Si tu ESP32-CAM está en una red local diferente a la instancia EC2, necesitarás:

1. **Usar una VPN** o
2. **Exponer el stream públicamente** (no recomendado por seguridad) o
3. **Usar túnel SSH** para hacer port forwarding

### Opción: Túnel SSH para desarrollo local

Si prefieres probar localmente mientras desarrollas:

```bash
ssh -i /ruta/a/tu/clave.pem -L 8081:192.168.18.30:81 ubuntu@3.16.78.139 -N
```

Luego configura `STREAM_URL=http://localhost:8081/stream`

## Solución de Problemas

### Error: "Cannot connect to the Docker daemon"
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Error: "No module named 'cv2'"
```bash
# Reconstruir la imagen
docker-compose build --no-cache
```

### Error: "Cannot open display"
La aplicación usa GUI (cv2.imshow). Si necesitas la interfaz gráfica, necesitarás configurar X11 forwarding o usar VNC.

### Para operar sin GUI, modifica los scripts para:
1. No usar `cv2.imshow()` 
2. Guardar frames como archivos
3. Mostrar resultados en consola

## Actualizar el Código

```bash
# En la instancia EC2
cd hardware_ESP32Cam
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

## Monitoreo

Para monitorear continuamente los logs:

```bash
docker-compose logs -f face-recognition
```

## Backup de Datos

Los archivos importantes están montados como volúmenes:
- `encodings.npy`
- `labels.json`
- `capturas_registro/`

Para hacer backup:
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz encodings.npy labels.json capturas_registro/
scp -i /ruta/a/tu/clave.pem ubuntu@3.16.78.139:~/hardware_ESP32Cam/backup-*.tar.gz ./
```

