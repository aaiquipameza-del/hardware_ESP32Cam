# Políticas IAM para Face Recognition API

Este directorio contiene las políticas IAM necesarias para desplegar y ejecutar la API de reconocimiento facial en AWS.

## Archivos Incluidos

### ec2-trust-policy.json
Documento de confianza para el rol IAM de EC2. Permite que el servicio EC2 asuma este rol.

**Uso:**
```bash
aws iam create-role \
  --role-name EC2-FaceRecognition-Role \
  --assume-role-policy-document file://iam-policies/ec2-trust-policy.json
```

### cloudwatch-policy.json
Política que permite escribir logs en CloudWatch Logs para el grupo de logs `/face-recognition/*`.

**Uso:**
```bash
aws iam put-role-policy \
  --role-name EC2-FaceRecognition-Role \
  --policy-name CloudWatchLogsPolicy \
  --policy-document file://iam-policies/cloudwatch-policy.json
```

### s3-backup-policy.json
Política que permite acceso de lectura/escritura al bucket S3 `face-recognition-backups` para backups.

**Nota:** Reemplaza `face-recognition-backups` con el nombre de tu bucket S3.

**Uso:**
```bash
aws iam put-role-policy \
  --role-name EC2-FaceRecognition-Role \
  --policy-name S3BackupPolicy \
  --policy-document file://iam-policies/s3-backup-policy.json
```

### ecr-policy.json
Política que permite extraer imágenes desde ECR (Elastic Container Registry).

**Uso:**
```bash
aws iam put-role-policy \
  --role-name ECS-TaskExecutionRole \
  --policy-name ECRPullPolicy \
  --policy-document file://iam-policies/ecr-policy.json
```

### ec2-deploy-policy.json
Política mínima para un usuario IAM que realiza despliegues en EC2.

**Uso:**
```bash
aws iam put-user-policy \
  --user-name face-recognition-deployer \
  --policy-name EC2DeployPolicy \
  --policy-document file://iam-policies/ec2-deploy-policy.json
```

## Instrucciones de Uso

1. **Revisar y personalizar:** Edita los archivos según tus necesidades, especialmente los nombres de recursos (buckets S3, grupos de logs, etc.).

2. **Crear roles:**
   ```bash
   # Crear rol para EC2
   aws iam create-role \
     --role-name EC2-FaceRecognition-Role \
     --assume-role-policy-document file://iam-policies/ec2-trust-policy.json
   
   # Adjuntar políticas
   aws iam put-role-policy \
     --role-name EC2-FaceRecognition-Role \
     --policy-name CloudWatchLogsPolicy \
     --policy-document file://iam-policies/cloudwatch-policy.json
   ```

3. **Crear instance profile:**
   ```bash
   aws iam create-instance-profile \
     --instance-profile-name EC2-FaceRecognition-Profile
   
   aws iam add-role-to-instance-profile \
     --instance-profile-name EC2-FaceRecognition-Profile \
     --role-name EC2-FaceRecognition-Role
   ```

4. **Asignar a instancia EC2:**
   - Desde CLI: Usa `--iam-instance-profile Name=EC2-FaceRecognition-Profile` al crear la instancia
   - Desde Console: EC2 → Instances → Actions → Security → Modify IAM role

## Seguridad

- **Principio de menor privilegio:** Estas políticas dan solo los permisos mínimos necesarios
- **Recursos específicos:** Modifica los ARNs de recursos para que apunten solo a tus recursos específicos
- **Revisar regularmente:** Revisa y actualiza las políticas periódicamente

## Referencias

Para más información, consulta:
- [AWS_DEPLOYMENT_COMPLETE.md](../AWS_DEPLOYMENT_COMPLETE.md) - Sección 3: Configuración IAM
- [AWS IAM Documentation](https://docs.aws.amazon.com/IAM/)

