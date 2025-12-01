# Guía de Despliegue en AWS

Esta guía cubre múltiples opciones para desplegar la API de reconocimiento facial en AWS.

## Tabla de Contenidos

1. [EC2 con Docker](#1-ec2-con-docker-recomendado)
2. [AWS Elastic Beanstalk](#2-aws-elastic-beanstalk)
3. [AWS ECS/Fargate](#3-aws-ecsfargate)
4. [Configuración de Seguridad](#configuración-de-seguridad)
5. [Monitoreo y Logs](#monitoreo-y-logs)

---

## 1. EC2 con Docker (Recomendado)

### Ventajas
- ✅ Control total sobre el entorno
- ✅ Fácil de configurar y mantener
- ✅ Ideal para aplicaciones con dependencias pesadas
- ✅ Costo predecible

### Pasos de Despliegue

#### 1.1 Crear Instancia EC2

1. **Accede a AWS Console** → EC2 → Launch Instance
2. **Configuración recomendada:**
   - **AMI**: Ubuntu 22.04 LTS (o Amazon Linux 2023)
   - **Instance Type**: `t3.medium` o superior (mínimo 2 vCPU, 4GB RAM)
   - **Storage**: 20GB mínimo
   - **Security Group**: 
     - Puerto 22 (SSH)
     - Puerto 5000 (Flask API) - o el puerto que uses
     - Puerto 80/443 (si usas nginx como reverse proxy)

3. **Crear/Seleccionar Key Pair** para acceso SSH
4. **Launch Instance**

#### 1.2 Configurar Security Group

```bash
# En AWS Console → EC2 → Security Groups
# Agregar reglas:
- Type: SSH, Port: 22, Source: My IP
- Type: Custom TCP, Port: 5000, Source: 0.0.0.0/0 (o tu IP específica)
```

#### 1.3 Conectarse a la Instancia

```bash
# Reemplaza con tu IP y ruta de clave
ssh -i ~/.ssh/tu-clave.pem ubuntu@<EC2_PUBLIC_IP>
```

#### 1.4 Instalar Docker en EC2

```bash
# Actualizar sistema
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt-get install -y docker-compose-plugin

# Verificar instalación
docker --version
docker compose version

# Reconectar para aplicar cambios de grupo
exit
```

#### 1.5 Clonar y Configurar el Proyecto

```bash
# Instalar Git si no está instalado
sudo apt-get install -y git

# Clonar repositorio
git clone https://github.com/tu-usuario/hardware_ESP32Cam.git
cd hardware_ESP32Cam

# Crear archivo .env
cat > .env << EOF
STREAM_URL=http://192.168.18.30:81/stream
FLASK_PORT=5000
EOF
```

#### 1.6 Desplegar con Docker Compose

```bash
# Construir y ejecutar
docker compose build
docker compose up -d

# Ver logs
docker compose logs -f

# Verificar estado
docker compose ps
```

#### 1.7 Configurar Nginx como Reverse Proxy (Opcional pero Recomendado)

```bash
# Instalar Nginx
sudo apt-get install -y nginx

# Crear configuración
sudo nano /etc/nginx/sites-available/face-recognition
```

Contenido del archivo de configuración:

```nginx
server {
    listen 80;
    server_name tu-dominio.com o EC2_IP;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Para streaming de video
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/face-recognition /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 1.8 Configurar SSL con Let's Encrypt (Opcional)

```bash
# Instalar Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtener certificado (requiere dominio)
sudo certbot --nginx -d tu-dominio.com

# Renovación automática
sudo certbot renew --dry-run
```

#### 1.9 Auto-inicio con Systemd

Crear servicio para auto-inicio:

```bash
sudo nano /etc/systemd/system/face-recognition.service
```

Contenido:

```ini
[Unit]
Description=Face Recognition API
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/hardware_ESP32Cam
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar servicio
sudo systemctl enable face-recognition.service
sudo systemctl start face-recognition.service
```

---

## 2. AWS Elastic Beanstalk

### Ventajas
- ✅ Gestión automática de infraestructura
- ✅ Escalado automático
- ✅ Health checks integrados
- ✅ Rollback automático

### Pasos de Despliegue

#### 2.1 Instalar EB CLI

```bash
# Instalar pip si no está instalado
python3 -m pip install --upgrade pip

# Instalar EB CLI
pip install awsebcli

# Verificar instalación
eb --version
```

#### 2.2 Preparar Aplicación para Elastic Beanstalk

Crear archivo `.ebextensions/python.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app:app
  aws:elasticbeanstalk:application:environment:
    STREAM_URL: http://192.168.18.30:81/stream
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
```

Crear archivo `.platform/hooks/postdeploy/01_install_dependencies.sh`:

```bash
#!/bin/bash
# Instalar dependencias del sistema para OpenCV
apt-get update
apt-get install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1
```

#### 2.3 Inicializar Elastic Beanstalk

```bash
# Desde el directorio del proyecto
eb init

# Seleccionar:
# - Region: tu región preferida
# - Application name: face-recognition-api
# - Platform: Python 3.11
# - Setup SSH: Yes
```

#### 2.4 Crear Entorno y Desplegar

```bash
# Crear entorno (primera vez)
eb create face-recognition-env \
  --instance-type t3.medium \
  --envvars STREAM_URL=http://192.168.18.30:81/stream

# O usar entorno existente
eb use face-recognition-env

# Desplegar
eb deploy

# Abrir en navegador
eb open
```

#### 2.5 Comandos Útiles

```bash
# Ver logs
eb logs

# Ver estado
eb status

# SSH al entorno
eb ssh

# Actualizar variables de entorno
eb setenv STREAM_URL=http://nueva-url/stream
```

**Nota**: Elastic Beanstalk puede tener limitaciones con dependencias pesadas como OpenCV. Considera usar Docker en lugar de la plataforma Python nativa.

---

## 3. AWS ECS/Fargate

### Ventajas
- ✅ Sin gestión de servidores
- ✅ Escalado automático
- ✅ Alta disponibilidad
- ✅ Integración con otros servicios AWS

### Pasos de Despliegue

#### 3.1 Crear ECR Repository

```bash
# Instalar AWS CLI si no está instalado
# https://aws.amazon.com/cli/

# Configurar credenciales
aws configure

# Crear repositorio ECR
aws ecr create-repository --repository-name face-recognition-api --region us-east-1

# Obtener URI del repositorio
aws ecr describe-repositories --repository-names face-recognition-api --region us-east-1
```

#### 3.2 Construir y Subir Imagen Docker

```bash
# Autenticarse en ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Construir imagen
docker build -t face-recognition-api .

# Tag imagen
docker tag face-recognition-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/face-recognition-api:latest

# Subir imagen
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/face-recognition-api:latest
```

#### 3.3 Crear Task Definition

Crear archivo `task-definition.json`:

```json
{
  "family": "face-recognition-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "face-recognition",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/face-recognition-api:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "STREAM_URL",
          "value": "http://192.168.18.30:81/stream"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/face-recognition-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 3.4 Registrar Task Definition

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 3.5 Crear Cluster y Servicio

```bash
# Crear cluster
aws ecs create-cluster --cluster-name face-recognition-cluster

# Crear servicio (requiere VPC, subnets, security group)
aws ecs create-service \
  --cluster face-recognition-cluster \
  --service-name face-recognition-service \
  --task-definition face-recognition-api \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### 3.6 Configurar Application Load Balancer (Recomendado)

```bash
# Crear ALB para acceso público
# Usar AWS Console o CLI para crear:
# - Application Load Balancer
# - Target Group apuntando al puerto 5000
# - Listener en puerto 80/443
```

---

## Configuración de Seguridad

### Security Groups

**Mínimo necesario:**
- Puerto 22 (SSH) - Solo desde tu IP
- Puerto 5000 (API) - Solo desde IPs autorizadas o usar ALB
- Puerto 80/443 (HTTP/HTTPS) - Público si usas ALB

### IAM Roles

Para ECS/Fargate, crear rol con permisos:
- `AmazonECSTaskExecutionRolePolicy`
- Acceso a ECR para pull de imágenes
- CloudWatch Logs para logging

### Secrets Management

Para variables sensibles, usar AWS Secrets Manager o Parameter Store:

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

---

## Monitoreo y Logs

### CloudWatch Logs

```bash
# Ver logs desde CLI
aws logs tail /ecs/face-recognition-api --follow

# O desde AWS Console
# CloudWatch → Log groups → /ecs/face-recognition-api
```

### CloudWatch Metrics

- CPU Utilization
- Memory Utilization
- Request Count
- Error Rate

### Alarmas

Crear alarmas para:
- CPU > 80%
- Memory > 80%
- Error rate > 5%
- No healthy targets (si usas ALB)

---

## Comparación de Opciones

| Característica | EC2 | Elastic Beanstalk | ECS/Fargate |
|---------------|-----|-------------------|-------------|
| **Costo** | Bajo-Medio | Medio | Medio-Alto |
| **Control** | Alto | Medio | Medio |
| **Escalado** | Manual | Automático | Automático |
| **Mantenimiento** | Alto | Bajo | Muy Bajo |
| **Complejidad** | Media | Baja | Media-Alta |
| **Ideal para** | Desarrollo/Producción pequeña | Aplicaciones web estándar | Microservicios/Producción |

---

## Recomendación

Para esta aplicación con dependencias pesadas (OpenCV, face_recognition):

1. **Desarrollo/Testing**: EC2 con Docker
2. **Producción pequeña-mediana**: EC2 con Docker + Nginx + SSL
3. **Producción grande/escalable**: ECS/Fargate con ALB

---

## Script de Despliegue Automatizado

Usa el script `deploy.sh` existente o crea uno personalizado:

```bash
# Ejemplo de uso
./deploy.sh <EC2_IP> <SSH_KEY_PATH>
```

---

## Troubleshooting

### Error: "Cannot connect to Docker daemon"
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Error: "Out of memory"
- Aumentar tamaño de instancia
- Reducir `DOWNSCALE` en el código
- Procesar menos frames por segundo

### Error: "Stream connection failed"
- Verificar que ESP32-CAM esté accesible desde EC2
- Considerar VPN o túnel SSH si están en redes diferentes
- Verificar firewall/security groups

### Logs no aparecen
```bash
# Verificar configuración de logging
docker compose logs -f
# O para ECS
aws logs tail /ecs/face-recognition-api --follow
```

---

## Costos Estimados (Región us-east-1)

- **EC2 t3.medium**: ~$30/mes
- **Elastic Beanstalk**: ~$30-50/mes (incluye EC2)
- **ECS Fargate (1 vCPU, 2GB)**: ~$30-40/mes
- **ALB**: ~$16/mes
- **Data Transfer**: Variable según uso

---

## Próximos Pasos

1. Configurar CI/CD con GitHub Actions o AWS CodePipeline
2. Implementar auto-scaling basado en CPU/Memory
3. Configurar backup automático de `encodings.npy` y `labels.json` en S3
4. Implementar health checks y monitoring avanzado
5. Configurar CDN (CloudFront) si necesitas servir contenido estático

