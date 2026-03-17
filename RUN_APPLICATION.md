# How to Run Intelli-Credit Application

## 🚀 Quick Start with Docker Compose (Recommended)

This is the **easiest and recommended way** to run the complete system with all services.

### Prerequisites
- Docker Desktop installed and running
- Ollama installed with `gpt-oss` model pulled

### Step 1: Start Ollama
```bash
# Start Ollama service
ollama serve

# Pull the required model (if not already done)
ollama pull gpt-oss
```

### Step 2: Start Application with Docker Compose
```bash
# Navigate to project root
cd credit-score-360

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Step 3: Access the Application
- **Web Interface**: http://localhost:3000 (Webtop Desktop)
- **Direct API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

## 🐍 Run Backend Only (Development Mode)

If you want to run just the backend for development:

### Prerequisites
- Python 3.11+
- Required Python packages
- Ollama running with gpt-oss model

### Step 1: Install Dependencies
```bash
# Navigate to backend directory
cd backend

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Start Ollama
```bash
# In a separate terminal
ollama serve
ollama pull gpt-oss
```

### Step 3: Run Backend
```bash
# From backend directory
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Access Backend
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

## 📋 Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gpt-oss
OLLAMA_TIMEOUT_SECONDS=120

# AWS Textract (Optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1

# External APIs (Optional)
ECOURTS_API_KEY=your_key
MCA21_API_KEY=your_key
NEWS_API_KEY=your_key
CIBIL_B2B_CLIENT_ID=your_client_id
CIBIL_B2B_CLIENT_SECRET=your_client_secret

# Business Logic
SECTOR_CAP_NBFC=500
SECTOR_CAP_MANUFACTURING=200
SECTOR_CAP_TRADING=100
SECTOR_CAP_SERVICES=150

OCR_CONFIDENCE_THRESHOLD=70
MAX_UPLOAD_SIZE_MB=50
CAM_OUTPUT_DIR=/tmp/cam_outputs

# API Timeouts (seconds)
API_TIMEOUTS_ECOURTS=30
API_TIMEOUTS_MCA21=30
API_TIMEOUTS_NEWS_API=30
API_TIMEOUTS_RBI_FEED=30

# DistilBERT Model
DISTILBERT_MODEL=distilbert-base-uncased

# Logging
LOG_LEVEL=INFO
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Ollama Not Running
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# Pull required model
ollama pull gpt-oss
```

#### 2. Docker Issues
```bash
# Check Docker status
docker --version
docker-compose --version

# Clean up Docker
docker system prune -a

# Rebuild containers
docker compose build --no-cache
```

#### 3. Python Dependencies
```bash
# Install requirements
pip install -r backend/requirements.txt

# Check Python version
python --version  # Should be 3.11+

# Install specific packages if needed
pip install fastapi uvicorn python-multipart
```

#### 4. Port Conflicts
```bash
# Check what's using ports
netstat -an | grep :8000
netstat -an | grep :3000

# Kill processes if needed
# On Windows: Use Task Manager
# On Linux/Mac: sudo kill -9 <PID>
```

#### 5. Permission Issues
```bash
# On Linux/Mac, fix permissions
chmod +x scripts/*.sh

# Create required directories
mkdir -p /tmp/cam_outputs
```

---

## 📊 Service Status Checks

### Health Endpoints
```bash
# Check overall health
curl http://localhost:8000/api/health

# Check individual services
curl http://localhost:8000/api/health

# Check job queue status
curl http://localhost:8000/api/jobs/queue/stats

# Check research components
curl http://localhost:8000/api/research/status
```

### Docker Service Status
```bash
# View all services
docker compose ps

# View logs for specific service
docker compose logs backend
docker compose logs webtop
docker compose logs nginx

# Restart specific service
docker compose restart backend
```

---

## 🚀 Production Deployment

### For Production Use

1. **Configure Environment Variables**
   - Set production values in `.env`
   - Configure SSL certificates
   - Set up proper logging

2. **Use Docker Compose**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Set Up Reverse Proxy**
   - Configure domain names
   - Set up SSL certificates
   - Configure load balancing

4. **Monitoring**
   - Set up log aggregation
   - Configure health checks
   - Set up alerting

---

## 📱 Access Points

### Web Interface
- **Main Application**: http://localhost:3000
- **Direct API**: http://localhost:8000

### API Endpoints
- **Health Check**: http://localhost:8000/api/health
- **Upload Documents**: http://localhost:8000/api/ingest
- **Credit Scoring**: http://localhost:8000/api/scoring
- **Research**: http://localhost:8000/api/research
- **Job Queue**: http://localhost:8000/api/jobs

### Documentation
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎯 Quick Test

### Test the System
```bash
# Test health check
curl http://localhost:8000/api/health

# Test document upload (example)
curl -X POST "http://localhost:8000/api/ingest" \
  -F "files=@test_document.pdf" \
  -F "document_types=financial_statement"

# Check job status
curl http://localhost:8000/api/jobs/queue/stats
```

---

## 📞 Support

If you encounter issues:

1. **Check Logs**: `docker compose logs -f`
2. **Verify Ollama**: `ollama list`
3. **Check Ports**: Ensure 8000 and 3000 are available
4. **Review Environment**: Check `.env` configuration

For detailed troubleshooting, see the README.md file or check the application logs.
