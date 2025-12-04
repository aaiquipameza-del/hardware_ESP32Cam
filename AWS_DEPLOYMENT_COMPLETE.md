# Guía Completa de Despliegue en AWS

Esta guía proporciona una documentación exhaustiva para desplegar la API de reconocimiento facial en AWS, incluyendo servicios utilizados, costos, configuración IAM y variables de entorno.

## Tabla de Contenidos

1. [Servicios AWS Utilizados](#1-servicios-aws-utilizados)
2. [Costos Estimados](#2-costos-estimados)
3. [Configuración IAM](#3-configuración-iam)
4. [Variables de Entorno](#4-variables-de-entorno)
5. [Checklist de Despliegue](#5-checklist-de-despliegue)
6. [Troubleshooting](#6-troubleshooting)
7. [Optimización de Costos](#7-optimización-de-costos)
8. [Referencias](#8-referencias)

---

## 1. Servicios AWS Utilizados

### 1.1 Servicios Principales

#### EC2 (Elastic Compute Cloud)

- **Propósito**: Instancia de computación para ejecutar la aplicación Docker
- **Configuración recomendada**:
  - Tipo de instancia: `t3.medium` (2 vCPU, 4GB RAM)
  - AMI: Ubuntu 22.04 LTS
  - Almacenamiento: 20GB GP3 SSD
  - Región: us-east-1 (N. Virginia) o la más cercana

#### VPC (Virtual Private Cloud) - Opcional pero recomendado

- **Propósito**: Red privada aislada para recursos AWS
- **Componentes**:
  - Subnets públicas/privadas
  - Internet Gateway
  - Route Tables
  - Security Groups

#### Security Groups

- **Propósito**: Firewall virtual para controlar tráfico de red
- **Reglas necesarias**:
  - SSH (22): Solo desde tu IP
  - HTTP (80): Público (si usas ALB/Nginx)
  - HTTPS (443): Público (si usas SSL)
  - Custom TCP (5000): Desde ALB o IPs específicas

#### ECR (Elastic Container Registry) - Para ECS/Fargate

- **Propósito**: Repositorio privado para imágenes Docker
- **Uso**: Almacenar y gestionar versiones de imágenes


#### Application Load Balancer (ALB) - Opcional

- **Propósito**: Distribuir tráfico, SSL termination, health checks
- **Uso**: Recomendado para producción con múltiples instancias

#### CloudWatch

- **Propósito**: Monitoreo, logs y métricas
- **Componentes**:
  - CloudWatch Logs: Almacenar logs de aplicación
  - CloudWatch Metrics: Métricas de CPU, memoria, etc.
  - CloudWatch Alarms: Alertas automáticas

#### S3 (Simple Storage Service) - Opcional

- **Propósito**: Backup de encodings.npy, labels.json, frames capturados
- **Ventaja**: Almacenamiento duradero y económico

#### Systems Manager Parameter Store / Secrets Manager

- **Propósito**: Almacenar variables de entorno sensibles
- **Uso**: Secrets como webhook URLs, tokens, etc.

### 1.2 Servicios Adicionales (Opcionales)

- **Route 53**: Gestión de DNS y dominio personalizado
- **Certificate Manager**: Certificados SSL/TLS gratuitos
- **CloudFront**: CDN para contenido estático
- **Elastic Beanstalk**: Alternativa simplificada de despliegue

---

## 2. Costos Estimados

### 2.1 Configuración Básica (EC2 Standalone)

**Región: us-east-1 (N. Virginia)**

| Servicio | Configuración | Costo Mensual Estimado |
|----------|---------------|------------------------|
| EC2 t3.medium | 730 horas/mes | ~$30.00 |
| EBS Storage (20GB GP3) | 20GB | ~$1.60 |
| Data Transfer Out | Primeros 100GB gratis | $0.00 |
| Elastic IP (si está activo) | 1 IP | $0.00 |
| **Total Estimado** | | **~$31.60/mes** |

### 2.2 Configuración con ALB (Producción)

| Servicio | Configuración | Costo Mensual Estimado |
|----------|---------------|------------------------|
| EC2 t3.medium | 730 horas/mes | ~$30.00 |
| Application Load Balancer | 1 ALB | ~$16.20 |
| LCU (Load Balancer Capacity Units) | ~1000 horas LCU | ~$8.00 |
| EBS Storage (20GB GP3) | 20GB | ~$1.60 |
| Data Transfer Out | 100GB | $0.00 (primeros 100GB gratis) |
| **Total Estimado** | | **~$55.80/mes** |

### 2.3 Configuración ECS/Fargate

| Servicio | Configuración | Costo Mensual Estimado |
|----------|---------------|------------------------|
| ECS Fargate (1 vCPU, 2GB) | 730 horas/mes | ~$30.00 |
| ECR Storage | 10GB | ~$1.00 |
| Application Load Balancer | 1 ALB | ~$16.20 |
| LCU | ~1000 horas LCU | ~$8.00 |
| CloudWatch Logs | 5GB/mes | ~$2.50 |
| **Total Estimado** | | **~$57.70/mes** |

### 2.4 Servicios Adicionales (Opcionales)

| Servicio | Costo Mensual |
|----------|---------------|
| S3 Storage (100GB) | ~$2.30 |
| CloudWatch Alarms (10 alarmas) | ~$0.00 (primeras 10 gratis) |
| Route 53 Hosted Zone | ~$0.50 |
| Certificate Manager | $0.00 (gratis) |

### 2.5 Notas sobre Costos

- **Free Tier**: Los primeros 12 meses incluyen 750 horas de t2.micro/t3.micro gratis
- **Ahorro**: Reservar instancias puede reducir costos en 30-40%
- **Optimización**: Usar t3.small puede reducir costos a ~$15/mes (revisar rendimiento)
- **Data Transfer**: Primeros 100GB salientes gratis, luego ~$0.09/GB

---

## 3. Configuración IAM

### 3.1 Roles IAM para EC2

#### Rol: `EC2-FaceRecognition-Role`

**Políticas adjuntas:**

- `AmazonEC2ReadOnlyAccess` (opcional, para monitoreo)
- Política personalizada para CloudWatch Logs (ver archivo `iam-policies/cloudwatch-policy.json`)

**Trust Relationship:**

Ver archivo `iam-policies/ec2-trust-policy.json` para el documento completo.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

#### Política Personalizada: CloudWatch Logs Write Access

Ver archivo `iam-policies/cloudwatch-policy.json` para la política completa.

#### Política Personalizada: S3 Backup Access (si usas S3)

Ver archivo `iam-policies/s3-backup-policy.json` para la política completa.

### 3.2 Roles IAM para ECS/Fargate

#### Rol: `ECS-TaskExecutionRole`

**Políticas adjuntas:**

- `AmazonECSTaskExecutionRolePolicy`
- Política para ECR (si es necesario)
- Política para Secrets Manager (si usas secrets)

#### Política para ECR:

Ver archivo `iam-policies/ecr-policy.json` para la política completa.

#### Rol: `ECS-TaskRole`

**Uso**: Para permisos de la aplicación dentro del contenedor

**Políticas:**

- CloudWatch Logs (similar a EC2)
- S3 Access (si la app necesita escribir a S3)
- Secrets Manager (para leer variables)

### 3.3 Usuario IAM para Deployment (Opcional)

#### Usuario: `face-recognition-deployer`

**Políticas:**

- `AmazonEC2FullAccess` (o limitado a acciones necesarias)
- `AmazonECS_FullAccess` (si usas ECS)
- `AmazonECRFullAccess` (si usas ECR)
- `IAMReadOnlyAccess` (para verificar roles)

**Política Mínima para EC2 Deployment:**

Ver archivo `iam-policies/ec2-deploy-policy.json` para la política completa.

### 3.4 Pasos para Crear Roles IAM

#### Paso 1: Crear Rol para EC2

```bash
# Desde AWS CLI
aws iam create-role \
  --role-name EC2-FaceRecognition-Role \
  --assume-role-policy-document file://iam-policies/ec2-trust-policy.json

# Adjuntar políticas
aws iam attach-role-policy \
  --role-name EC2-FaceRecognition-Role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy

# Crear instance profile
aws iam create-instance-profile \
  --instance-profile-name EC2-FaceRecognition-Profile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-FaceRecognition-Profile \
  --role-name EC2-FaceRecognition-Role
```

#### Paso 2: Asignar Rol a Instancia EC2

```bash
# Al crear la instancia (via CLI)
aws ec2 run-instances \
  --image-id ami-xxx \
  --instance-type t3.medium \
  --iam-instance-profile Name=EC2-FaceRecognition-Profile \
  --key-name tu-key-pair \
  --security-group-ids sg-xxx

# O desde AWS Console:
# EC2 → Instances → Actions → Security → Modify IAM role
```

---

## 4. Variables de Entorno

### 4.1 Variables Requeridas

| Variable | Descripción | Ejemplo | Default |
|----------|-------------|---------|---------|
| `STREAM_URL` | URL del stream del ESP32-CAM | `http://192.168.1.100:81/stream` | `http://192.168.122.116:81/stream` |
| `FLASK_PORT` | Puerto donde corre Flask | `5000` | `5000` |
| `FLASK_ENV` | Entorno de Flask | `production` | `development` |

### 4.2 Variables Opcionales

| Variable | Descripción | Ejemplo | Uso |
|----------|-------------|---------|-----|
| `NEXTJS_WEBHOOK_URL` | URL del webhook de Next.js | `https://api.tudominio.com/webhook` | Integración frontend |
| `FACIAL_RECOGNITION_WEBHOOK_SECRET` | Token secreto para webhook | `secret-token-123` | Autenticación webhook |
| `AWS_REGION` | Región de AWS | `us-east-1` | Servicios AWS |
| `LOG_LEVEL` | Nivel de logging | `INFO`, `DEBUG`, `WARNING` | Control de logs |
| `DOWNSCALE` | Factor de reducción de frames | `0.5` | Rendimiento |
| `THRESHOLD` | Umbral de reconocimiento | `0.6` | Precisión |

### 4.3 Configuración en EC2

#### Opción 1: Archivo `.env` (Docker Compose)

Ver archivo `.env.example` para un template completo.

```bash
# Crear archivo .env basado en el template
cp .env.example .env
# Editar .env con tus valores
nano .env
```

#### Opción 2: Variables de Entorno del Sistema

```bash
# En /etc/environment o ~/.bashrc
export STREAM_URL="http://192.168.1.100:81/stream"
export FLASK_PORT="5000"
export FLASK_ENV="production"
```

#### Opción 3: Systemd Service (para auto-start)

```ini
[Service]
Environment="STREAM_URL=http://192.168.1.100:81/stream"
Environment="FLASK_PORT=5000"
Environment="FLASK_ENV=production"
```

### 4.4 Configuración en ECS/Fargate

#### Usando Task Definition:

```json
{
  "containerDefinitions": [{
    "environment": [
      {"name": "STREAM_URL", "value": "http://192.168.1.100:81/stream"},
      {"name": "FLASK_PORT", "value": "5000"},
      {"name": "FLASK_ENV", "value": "production"}
    ],
    "secrets": [
      {
        "name": "FACIAL_RECOGNITION_WEBHOOK_SECRET",
        "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:webhook-secret"
      }
    ]
  }]
}
```

#### Usando Secrets Manager:

```bash
# Crear secret
aws secretsmanager create-secret \
  --name face-recognition/env \
  --secret-string '{
    "STREAM_URL": "http://192.168.1.100:81/stream",
    "WEBHOOK_SECRET": "secret-token-123"
  }'

# En Task Definition, usar:
"secrets": [
  {
    "name": "STREAM_URL",
    "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:face-recognition/env:STREAM_URL::"
  }
]
```

#### Usando Parameter Store:

```bash
# Crear parámetros
aws ssm put-parameter \
  --name "/face-recognition/stream-url" \
  --value "http://192.168.1.100:81/stream" \
  --type "String"

aws ssm put-parameter \
  --name "/face-recognition/webhook-secret" \
  --value "secret-token-123" \
  --type "SecureString"

# En Task Definition:
"secrets": [
  {
    "name": "STREAM_URL",
    "valueFrom": "arn:aws:ssm:us-east-1:123456789:parameter/face-recognition/stream-url"
  }
]
```

### 4.5 Carga de Variables en Código Python

Actualizar `app.py` para leer desde Secrets Manager (opcional):

```python
import os
import boto3
import json

def load_secrets():
    """Cargar variables desde AWS Secrets Manager"""
    secret_name = os.getenv('AWS_SECRET_NAME', '')
    if not secret_name:
        return {}
    
    try:
        client = boto3.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Warning: Could not load secrets: {e}")
        return {}

# Cargar secrets al inicio
secrets = load_secrets()
STREAM_URL = os.getenv('STREAM_URL', secrets.get('STREAM_URL', 'http://192.168.122.116:81/stream'))
WEBHOOK_SECRET = os.getenv('FACIAL_RECOGNITION_WEBHOOK_SECRET', secrets.get('WEBHOOK_SECRET', ''))
```

---

## 5. Checklist de Despliegue

### Pre-requisitos

- [ ] Cuenta AWS activa
- [ ] AWS CLI configurado (opcional)
- [ ] Key Pair creado para EC2
- [ ] Repositorio Git configurado
- [ ] Archivos `encodings.npy` y `labels.json` disponibles

### Configuración AWS

- [ ] VPC creada (o usar default)
- [ ] Security Group configurado
- [ ] Rol IAM creado y asignado a EC2
- [ ] Instancia EC2 creada
- [ ] Elastic IP asignada (opcional)

### Despliegue

- [ ] Docker instalado en EC2
- [ ] Código clonado/actualizado
- [ ] Variables de entorno configuradas (usar `.env.example` como base)
- [ ] Contenedor construido y ejecutándose
- [ ] Health check exitoso

### Post-Despliegue

- [ ] Logs funcionando (CloudWatch)
- [ ] Alarmas configuradas
- [ ] Backup de datos configurado (S3)
- [ ] SSL/HTTPS configurado (opcional)
- [ ] Documentación actualizada

---

## 6. Troubleshooting

### Problemas Comunes

**Error: "Access Denied" en CloudWatch**

- Verificar que el rol IAM tenga permisos de CloudWatch Logs
- Verificar que la instancia tenga el rol asignado
- Verificar políticas IAM en `iam-policies/cloudwatch-policy.json`

**Variables de entorno no se cargan**

- Verificar formato del archivo `.env`
- Verificar que docker-compose esté leyendo `.env`
- Verificar logs del contenedor: `docker compose logs`
- Comparar con `.env.example` para verificar formato correcto

**Costo más alto de lo esperado**

- Verificar instancias detenidas (aún cobran storage)
- Revisar Data Transfer Out
- Verificar Elastic IPs no asociadas
- Revisar sección 7 sobre optimización de costos

**Error de conexión al stream**

- Verificar que ESP32-CAM esté accesible desde EC2
- Verificar Security Groups y firewall
- Verificar `STREAM_URL` en variables de entorno

---

## 7. Optimización de Costos

1. **Reservar Instancias**: Ahorro de 30-40% comprometiéndote a 1-3 años
2. **Spot Instances**: Para desarrollo/testing, ahorro de hasta 90%
3. **Auto Scaling**: Apagar instancias cuando no se usen (desarrollo)
4. **S3 Lifecycle Policies**: Mover datos antiguos a Glacier
5. **CloudWatch Logs Retention**: Configurar retención de logs (1-30 días)

### Ejemplo de Lifecycle Policy para S3

```json
{
  "Rules": [
    {
      "Id": "MoveOldFramesToGlacier",
      "Status": "Enabled",
      "Prefix": "captured_frames/",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

---

## 8. Referencias

- [AWS EC2 Pricing](https://aws.amazon.com/ec2/pricing/)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [EC2 Security Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-security-groups.html)

---

## Notas Finales

Esta guía cubre los aspectos esenciales para desplegar la aplicación en AWS. Para más detalles sobre configuración específica, consulta:

- `AWS_DEPLOYMENT.md` - Guía detallada de despliegue paso a paso
- `AWS_QUICKSTART.md` - Inicio rápido para despliegue
- `DEPLOY_EC2.md` - Guía específica para EC2
- Archivos en `iam-policies/` - Políticas IAM completas

