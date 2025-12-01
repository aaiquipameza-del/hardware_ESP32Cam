# AWS Deployment Quick Start

Guía rápida para desplegar la API en AWS en 10 minutos.

## Opción 1: EC2 con Docker (Más Rápido)

### Paso 1: Crear Instancia EC2
1. AWS Console → EC2 → Launch Instance
2. Seleccionar: **Ubuntu 22.04 LTS**
3. Instance Type: **t3.medium** (2 vCPU, 4GB RAM)
4. Security Group: Agregar reglas:
   - SSH (22) desde tu IP
   - Custom TCP (5000) desde 0.0.0.0/0
5. Crear/Seleccionar Key Pair
6. Launch Instance

### Paso 2: Conectarse y Configurar

```bash
# Conectarse
ssh -i ~/.ssh/tu-clave.pem ubuntu@<EC2_IP>

# Instalar Docker (copiar y pegar todo)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt-get install -y docker-compose-plugin
exit

# Reconectar
ssh -i ~/.ssh/tu-clave.pem ubuntu@<EC2_IP>

# Clonar proyecto
git clone https://github.com/tu-usuario/hardware_ESP32Cam.git
cd hardware_ESP32Cam

# Crear .env
echo "STREAM_URL=http://192.168.18.30:81/stream" > .env

# Desplegar
docker compose up -d --build

# Ver logs
docker compose logs -f
```

### Paso 3: Verificar

Abre en navegador: `http://<EC2_IP>:5000`

---

## Opción 2: Usar Script Automatizado

```bash
# Desde tu máquina local
chmod +x deploy.sh
./deploy.sh <EC2_IP> ~/.ssh/tu-clave.pem
```

**Nota**: Edita `deploy.sh` y actualiza `REPO_URL` con tu repositorio.

---

## Configuración Rápida de Nginx (Opcional)

```bash
# En EC2
sudo apt-get install -y nginx

# Crear configuración
sudo tee /etc/nginx/sites-available/face-recognition > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Habilitar
sudo ln -s /etc/nginx/sites-available/face-recognition /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

---

## Checklist Pre-Despliegue

- [ ] Repositorio en GitHub/GitLab
- [ ] Instancia EC2 creada
- [ ] Security Group configurado (puertos 22, 5000)
- [ ] Key Pair descargado
- [ ] STREAM_URL del ESP32-CAM disponible
- [ ] Archivos `encodings.npy` y `labels.json` en el repo (o subirlos después)

---

## Comandos Útiles Post-Despliegue

```bash
# Ver estado
docker compose ps

# Ver logs
docker compose logs -f

# Reiniciar
docker compose restart

# Actualizar código
git pull
docker compose down
docker compose up -d --build

# Detener
docker compose down
```

---

## Troubleshooting Rápido

**No puedo acceder a la API:**
```bash
# Verificar que el contenedor está corriendo
docker compose ps

# Verificar logs de errores
docker compose logs

# Verificar security group en AWS Console
```

**Error de memoria:**
- Cambiar a instancia más grande (t3.large)
- O reducir DOWNSCALE en app.py

**Stream no funciona:**
- Verificar que ESP32-CAM esté accesible desde EC2
- Probar: `curl http://192.168.18.30:81/stream` desde EC2

---

## Costos

- **t3.medium**: ~$30/mes (~$0.04/hora)
- **t3.large**: ~$60/mes (~$0.08/hora)
- **Data Transfer**: Primeros 100GB gratis/mes

---

## Próximos Pasos

1. Configurar dominio y SSL (Let's Encrypt)
2. Configurar auto-backup de datos a S3
3. Configurar monitoreo con CloudWatch
4. Implementar CI/CD

Para más detalles, ver [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)

