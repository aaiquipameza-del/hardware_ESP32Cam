# EC2 Deployment Guide

## Quick Deploy

### Prerequisites
- [ ] EC2 instance running (Ubuntu 22.04 LTS recommended)
- [ ] Security Group configured:
  - Port 22 (SSH) from your IP
  - Port 5000 (Flask API) from 0.0.0.0/0 or specific IPs
- [ ] SSH key (.pem file) downloaded
- [ ] EC2 public IP address

### Option 1: Automated Deployment (Recommended)

```bash
# Make sure deploy.sh is executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh <EC2_IP_ADDRESS> <PATH_TO_SSH_KEY>

# Example:
./deploy.sh 3.16.78.139 ~/.ssh/my-key.pem
```

The script will:
1. ✅ Install Docker if needed
2. ✅ Clone/update repository
3. ✅ Copy necessary files
4. ✅ Build Docker image
5. ✅ Start containers
6. ✅ Show deployment status

### Option 2: Manual Deployment

#### Step 1: Connect to EC2
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
```

#### Step 2: Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt-get install -y docker-compose-plugin
exit
```

#### Step 3: Reconnect and Clone Repository
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
git clone https://github.com/YOUR_USERNAME/hardware_ESP32Cam.git
cd hardware_ESP32Cam
```

#### Step 4: Configure Environment
```bash
# Create .env file with your stream URL
echo "STREAM_URL=http://YOUR_ESP32_IP:81/stream" > .env
echo "FLASK_PORT=5000" >> .env
```

#### Step 5: Deploy
```bash
docker compose up -d --build
```

#### Step 6: Verify
```bash
# Check container status
docker compose ps

# View logs
docker compose logs -f

# Test API
curl http://localhost:5000/health
```

### Access Your API

Once deployed, access your API at:
- **Local (from EC2)**: `http://localhost:5000`
- **External**: `http://<EC2_IP>:5000`

### Important Files

Make sure these files exist before deployment:
- ✅ `app.py` - Main Flask application
- ✅ `Dockerfile` - Docker image configuration
- ✅ `docker-compose.yml` - Container orchestration
- ✅ `requirements.txt` - Python dependencies
- ✅ `encodings.npy` - Face encodings (if you have registered faces)
- ✅ `labels.json` - Face labels (if you have registered faces)

### Update Repository URL

If your repository URL is different, edit `deploy.sh` line 49:
```bash
REPO_URL="https://github.com/YOUR_USERNAME/hardware_ESP32Cam.git"
```

### Troubleshooting

**Cannot connect via SSH:**
- Verify Security Group allows port 22 from your IP
- Check that your key file has correct permissions: `chmod 400 ~/.ssh/your-key.pem`

**Docker permission denied:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Container fails to start:**
```bash
# Check logs
docker compose logs

# Check if port is already in use
sudo lsof -i :5000
```

**API not accessible externally:**
- Verify Security Group allows port 5000
- Check EC2 instance is running
- Verify container is running: `docker compose ps`

### Post-Deployment

**View logs:**
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP>
cd hardware_ESP32Cam
docker compose logs -f
```

**Restart service:**
```bash
docker compose restart
```

**Update code:**
```bash
git pull
docker compose down
docker compose up -d --build
```

**Stop service:**
```bash
docker compose down
```

### Next Steps

1. **Configure Nginx** (optional) - See `AWS_DEPLOYMENT.md` section 1.7
2. **Setup SSL** (optional) - See `AWS_DEPLOYMENT.md` section 1.8
3. **Configure Auto-start** - See `AWS_DEPLOYMENT.md` section 1.9
4. **Setup Monitoring** - Configure CloudWatch alarms


