# Azure Deployment Guide for Intelli-Credit
**Domain**: intelcredit.truvgo.tech  
**Server**: 4.213.160.42 (Standard_B4as_v2)

## 🚀 Quick Deployment Steps

### Step 1: Connect to Azure Server
```bash
ssh varshith@4.213.160.42
# Password: #varshith88
```

### Step 2: Setup Domain & SSL
```bash
# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx -y

# Configure Nginx for intelcredit.truvgo.tech
sudo nano /etc/nginx/sites-available/intelcredit
```

**Nginx Configuration** (`/etc/nginx/sites-available/intelcredit`):
```nginx
server {
    listen 80;
    server_name intelcredit.truvgo.tech;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/intelcredit /etc/nginx/sites-enabled/

# Get SSL certificate
sudo certbot --nginx -d intelcredit.truvgo.tech --email admin@truvgo.tech

# Test Nginx
sudo nginx -t
sudo systemctl restart nginx
```

### Step 3: Deploy Intelli-Credit Application
```bash
# Clone repository
git clone https://github.com/varshith-dev/creditcore360.git .

# Navigate to application directory
cd /opt/intellicredit

# Set permissions
sudo chown -R varshith:varshith /opt/intellicredit
```

### Step 4: Configure Environment
```bash
# Create environment file
cat > .env << 'EOF'
# Production Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API Configuration
REACT_APP_API_URL=https://intelcredit.truvgo.tech
OLLAMA_BASE_URL=http://ollama:11434

# Security Settings
CORS_ORIGINS=https://intelcredit.truvgo.tech
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Resource Limits
MAX_UPLOAD_SIZE_MB=100
OCR_CONFIDENCE_THRESHOLD=75

# Business Logic
SECTOR_CAP_NBFC=500
SECTOR_CAP_MANUFACTURING=200
SECTOR_CAP_TRADING=100
SECTOR_CAP_SERVICES=150
EOF
```

**Environment Variables** (`.env`):
```env
# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gpt-oss
OLLAMA_TIMEOUT_SECONDS=120

# Business Logic
SECTOR_CAP_NBFC=500
SECTOR_CAP_MANUFACTURING=200
SECTOR_CAP_TRADING=100
SECTOR_CAP_SERVICES=150

OCR_CONFIDENCE_THRESHOLD=70
MAX_UPLOAD_SIZE_MB=50
CAM_OUTPUT_DIR=/tmp/cam_outputs

# API Timeouts
API_TIMEOUTS_ECOURTS=30
API_TIMEOUTS_MCA21=30
API_TIMEOUTS_NEWS_API=30
API_TIMEOUTS_RBI_FEED=30

# DistilBERT Model
DISTILBERT_MODEL=distilbert-base-uncased

# Logging
LOG_LEVEL=INFO

# Production Settings
ENVIRONMENT=production
DEBUG=false
```

### Step 5: Start Services
```bash
# Deploy with production configuration
docker compose -f docker-compose.prod.yml up -d --build

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check status
docker compose -f docker-compose.prod.yml ps
```

## 📋 Complete Deployment Script

Save this as `deploy.sh` and run it:

```bash
#!/bin/bash
set -e

echo "🚀 Deploying Intelli-Credit to Azure..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker and required packages
echo "🐳 Installing Docker and required packages..."
sudo apt install nginx certbot python3-certbot-nginx docker.io docker-compose git -y

# Start and enable Docker
echo "🐳 Starting Docker..."
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Setup Nginx configuration
echo "🌐 Setting up Nginx configuration..."
sudo tee /etc/nginx/sites-available/intelcredit > /dev/null << 'EOF'
server {
    listen 80;
    server_name intelcredit.truvgo.tech;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/intelcredit /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Get SSL certificate
echo "🔒 Setting up SSL certificate..."
sudo certbot --nginx -d intelcredit.truvgo.tech --non-interactive --agree-tos --email admin@truvgo.tech

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/intellicredit
sudo chown $USER:$USER /opt/intellicredit

# Navigate to application directory
cd /opt/intellicredit

# Clone repository (replace with actual repo)
echo "📥 Cloning application repository..."
git clone <your-repo-url> .

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > .env << 'EOF'
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gpt-oss
OLLAMA_TIMEOUT_SECONDS=120
SECTOR_CAP_NBFC=500
SECTOR_CAP_MANUFACTURING=200
SECTOR_CAP_TRADING=100
SECTOR_CAP_SERVICES=150
OCR_CONFIDENCE_THRESHOLD=70
MAX_UPLOAD_SIZE_MB=50
CAM_OUTPUT_DIR=/tmp/cam_outputs
API_TIMEOUTS_ECOURTS=30
API_TIMEOUTS_MCA21=30
API_TIMEOUTS_NEWS_API=30
API_TIMEOUTS_RBI_FEED=30
DISTILBERT_MODEL=distilbert-base-uncased
LOG_LEVEL=INFO
ENVIRONMENT=production
DEBUG=false
EOF

# Start Ollama
echo "🤖 Starting Ollama..."
ollama serve &
sleep 5

# Pull AI model
echo "📥 Downloading AI model..."
ollama pull gpt-oss

# Deploy application
echo "🚀 Deploying Intelli-Credit application..."
docker compose up -d --build

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check deployment
echo "✅ Checking deployment status..."
docker compose ps

# Test health endpoint
echo "🔍 Testing health endpoint..."
curl -f http://localhost:8000/api/health || echo "⚠️ Health check failed"

echo "🎉 Deployment complete!"
echo "📱 Access your application at: https://intelcredit.truvgo.tech"
echo "📊 API documentation: https://intelcredit.truvgo.tech/docs"
echo "🔍 Health check: https://intelcredit.truvgo.tech/api/health"
```

## 🔧 Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: intelli-credit-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - /tmp/cam_outputs:/tmp/cam_outputs
      - /var/log/intelli-credit:/var/log/intelli-credit
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env
    networks:
      - intelli-credit-network

  webtop:
    image: lscr.io/linuxserver/webtop:ubuntu-xfce
    container_name: intelli-credit-webtop
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - /opt/intellicredit:/config
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Asia/Kolkata
    networks:
      - intelli-credit-network

networks:
  intelli-credit-network:
    driver: bridge
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Check application health
curl https://intelcredit.truvgo.tech/api/health

# Check Docker containers
docker compose ps

# View logs
docker compose logs -f backend

# Check system resources
free -h
df -h
htop
```

### Backup Strategy
```bash
# Create backup script
nano backup.sh

#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/intellicredit"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application data
docker compose exec backend tar -czf /tmp/app_backup_$DATE.tar.gz /app
docker cp intelli-credit-backend:/tmp/app_backup_$DATE.tar.gz $BACKUP_DIR/

# Backup CAM outputs
tar -czf $BACKUP_DIR/cam_outputs_$DATE.tar.gz /tmp/cam_outputs

echo "Backup completed: $BACKUP_DIR"
```

### Log Rotation
```bash
# Setup log rotation
sudo nano /etc/logrotate.d/intellicredit

/var/log/intelli-credit/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 varshith varshith
    postrotate
        docker compose restart backend
    endscript
}
```

## 🔒 Security Hardening

### Firewall Setup
```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 3000/tcp  # Block direct webtop access
sudo ufw status
```

### SSL Auto-Renewal
```bash
# Setup automatic SSL renewal
sudo crontab -e

# Add this line for monthly renewal:
0 2 1 * * /usr/bin/certbot renew --quiet
```

## 🚀 Access Points

After deployment, access the application at:

- **Main Application**: https://intelcredit.truvgo.tech
- **API Documentation**: https://intelcredit.truvgo.tech/docs
- **Health Check**: https://intelcredit.truvgo.tech/api/health
- **Job Queue Status**: https://intelcredit.truvgo.tech/api/jobs/queue/stats

## 📱 Testing the Deployment

```bash
# Test API endpoints
curl https://intelcredit.truvgo.tech/api/health

# Test document upload (example)
curl -X POST "https://intelcredit.truvgo.tech/api/ingest" \
  -F "files=@test_document.pdf" \
  -F "document_types=financial_statement"

# Check job queue
curl https://intelcredit.truvgo.tech/api/jobs/queue/stats
```

## 🎯 Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 80, 443, 8000 are available
2. **SSL Issues**: Check certificate status with `sudo certbot certificates`
3. **Docker Issues**: Restart with `docker compose restart`
4. **Ollama Issues**: Ensure model is pulled and service is running

### Log Locations
- **Application Logs**: `/var/log/intelli-credit/`
- **Docker Logs**: `docker compose logs -f`
- **Nginx Logs**: `/var/log/nginx/`
- **System Logs**: `journalctl -u docker`

## 📞 Support

For deployment issues:
1. Check logs: `docker compose logs -f`
2. Verify services: `docker compose ps`
3. Test health: `curl https://intelcredit.truvgo.tech/api/health`
4. Review configuration: Check `.env` and Nginx settings

The Intelli-Credit system is now deployed and accessible at **https://intelcredit.truvgo.tech**! 🎉
