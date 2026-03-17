# Intelli-Credit — AI-Powered Corporate Credit Appraisal Engine

An end-to-end AI-powered Credit Decisioning Engine for India's mid-market lending landscape, built with Python FastAPI backend and modern web frontend.

## 🏗️ Architecture Overview

The system runs entirely on a **self-hosted Azure VM** with three main pillars:

### 📊 Pillar 1: Data Ingestor
- **OCR Pipeline**: Tesseract + OpenCV preprocessing with confidence scoring
- **AWS Textract Fallback**: For low-confidence documents  
- **Field Extraction**: Ollama-powered structured data extraction
- **Cross-Validation**: 5 automated validation checks (GST ITC mismatch, revenue inflation, etc.)

### 🔍 Pillar 2: Research Agent  
- **External API Integration**: e-Courts, MCA21, News, RBI feeds
- **Officer Portal**: DistilBERT NLP classifier for field observations
- **Risk Synthesis**: Ollama-powered research analysis

### 📈 Pillar 3: Recommendation Engine
- **Five Cs Scoring**: Weighted credit scoring model (Character 25%, Capacity 30%, Capital 20%, Collateral 15%, Conditions 10%)
- **CIBIL Integration**: TransUnion B2B API for credit bureau data
- **Loan Limit Calculator**: Three-ceiling methodology (cash flow, asset-based, sector exposure)
- **CAM Generator**: Automated Credit Appraisal Memo generation (Word + PDF)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Ollama with `gpt-oss` model pulled
- Azure VM (Standard_B4as_v2: 4 vCPU, 16 GB RAM, 128 GB SSD)

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd credit-score-360
```

2. **Configure Environment**
```bash
# Copy and edit environment variables
cp .env.example .env
# Edit with your API keys and settings
```

3. **Start Services**
```bash
docker compose up -d
```

4. **Access Application**
- Webtop Desktop: `http://localhost:3000`
- API: `http://localhost:8000`
- Production: `https://system.truvgo.tech`

## 📁 Project Structure

```
intelli-credit/
├── docker-compose.yml              # Multi-service orchestration
├── nginx/
│   ├── default.conf            # Reverse proxy configuration
│   └── Dockerfile
├── backend/
│   ├── Dockerfile              # Python application container
│   ├── requirements.txt         # Python dependencies
│   ├── main.py               # FastAPI application entrypoint
│   ├── config.py             # Environment configuration
│   ├── shared/               # Shared utilities
│   │   ├── ollama_client.py # Ollama API wrapper
│   │   ├── models.py        # Pydantic data models
│   │   └── exceptions.py    # Custom exceptions
│   ├── pillar1_ingestor/     # Data ingestion pipeline
│   │   ├── ocr_pipeline.py
│   │   ├── textract_fallback.py
│   │   ├── field_extractor.py
│   │   ├── cross_validator.py
│   │   └── document_router.py
│   ├── pillar2_research/       # External research (placeholder)
│   ├── pillar3_engine/         # Credit decisioning engine
│   │   ├── five_cs_scorer.py
│   │   ├── cibil_client.py
│   │   ├── loan_limit_calc.py
│   │   └── cam_generator.py
│   ├── api/                  # FastAPI route handlers
│   │   ├── health.py
│   │   ├── ingest.py
│   │   ├── research.py
│   │   ├── scoring.py
│   │   └── jobs.py
│   └── frontend/              # Web UI
│       ├── templates/
│       │   ├── base.html
│       │   ├── upload.html
│       │   ├── officer_portal.html
│       │   ├── results.html
│       │   └── cam_preview.html
│       └── static/
│           └── styles.css
└── cam_outputs/               # Generated CAM documents
```

## 🔧 Configuration

### Environment Variables

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gpt-oss
OLLAMA_TIMEOUT_SECONDS=120

# AWS Textract (optional)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1

# External APIs (optional)
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
```

## 📊 Features

### Document Processing
- **Multi-format Support**: PDF, Excel, Images (JPG, PNG, TIFF)
- **Bilingual OCR**: English + Hindi with Tesseract
- **Intelligent Fallback**: AWS Textract for low-confidence documents
- **Structured Extraction**: AI-powered field extraction for financial statements, bank statements, GST returns, ITR, legal documents

### Risk Assessment
- **5 Cross-Validation Checks**: 
  - GST ITC mismatch detection
  - Revenue inflation analysis (ITR vs GST)
  - TDS vs headcount validation
  - Cash leakage detection
  - Circular trading pattern analysis
- **Real-time Risk Flagging**: Severity-based categorization

### Credit Scoring
- **Five Cs Model**: Industry-standard credit assessment framework
- **Automated Grading**: LOW_RISK, MODERATE_RISK, HIGH_RISK, DECLINE
- **CIBIL Integration**: Real-time credit bureau data
- **Dynamic Loan Limits**: Three-ceiling methodology with binding analysis

### User Interface
- **Modern Web UI**: Bootstrap 5 + custom styling
- **Four Core Screens**:
  1. **Upload**: Drag-and-drop document processing
  2. **Officer Portal**: Field observations with keyword detection
  3. **Results**: Interactive dashboard with Five Cs radar chart
  4. **CAM Preview**: Executive summary with download options

## 🔄 API Endpoints

### Health & Status
- `GET /health` - System health check
- `GET /api/health` - Detailed service status

### Document Processing  
- `POST /api/ingest` - Upload and process documents
- `GET /api/ingest/formats` - Supported file formats

### Credit Analysis
- `POST /api/scoring/five-cs` - Calculate Five Cs scores
- `POST /api/scoring/loan-limit` - Calculate loan limits
- `POST /api/scoring/cam` - Generate CAM document
- `GET /api/scoring/grade/{score}` - Get credit grade

### Research & Jobs
- `POST /api/research` - Run external research
- `POST /api/officer-observations` - Process field observations
- `POST /api/jobs/start` - Start background analysis job
- `GET /api/jobs/{job_id}/status` - Check job progress

## 🎯 Credit Scoring Logic

### Five Cs Weights
- **Character (25%)**: Compliance history + CIBIL + management quality
- **Capacity (30%)**: DSCR + cash flow analysis + operational efficiency  
- **Capital (20%)**: Net worth ratio + financial stability
- **Collateral (15%)**: Asset valuation + security coverage
- **Conditions (10%)**: Sector risk + regulatory environment

### Risk Grading
- **85-100**: LOW_RISK (Green) - Auto-approve
- **70-84**: MODERATE_RISK (Yellow) - Standard underwriting
- **50-69**: HIGH_RISK (Orange) - Senior approval required
- **<50**: DECLINE (Red) - Reject application

### Loan Limit Methodology
1. **Cash Flow Ceiling**: 4 × DSCR-adjusted free cash flow
2. **Asset Ceiling**: 60% of net tangible assets  
3. **Sector Ceiling**: Pre-configured exposure limits by sector
4. **Final Limit**: Minimum of three ceilings

## 🚨 Risk Validation Rules

### Automated Checks
1. **GST ITC Mismatch**: `abs(GSTR2A_ITC - GSTR3B_ITC) / GSTR3B_ITC > 15%`
2. **Revenue Inflation**: `abs(ITR_Income - GST_Turnover) / GST_Turnover > 25%`
3. **TDS vs Headcount**: Implied vs declared headcount variance > 40%
4. **Cash Leakage**: Cash withdrawals > 30% of declared opex
5. **Circular Trading**: NetworkX graph analysis of GST invoice patterns

### Severity Classification
- **CRITICAL**: Immediate attention required (winding up, NCLT cases)
- **HIGH**: Significant risk factors (major defaults, fraud indicators)
- **MEDIUM**: Moderate concerns (payment delays, compliance issues)  
- **LOW**: Minor observations (documentation gaps, minor discrepancies)

## 📄 CAM Generation

### Document Features
- **Executive Summary**: 3-line decision summary with key metrics
- **Five Cs Sections**: AI-generated narratives for each C
- **Risk Analysis**: Consolidated risk flags with severity
- **CIBIL Summary**: Credit bureau integration results
- **Loan Structure**: Detailed terms and binding analysis
- **Field Observations**: Officer visit notes (verbatim)
- **Model Explainability**: SHAP feature importance charts

### Output Formats
- **Microsoft Word (.docx)**: Full editing capability
- **PDF**: Professional document sharing
- **Automated Storage**: `/tmp/cam_outputs/` with timestamped filenames

## 🔒 Security & Compliance

### Data Protection
- **Local Processing**: No borrower data leaves the server
- **API Key Security**: Environment variable storage
- **Input Validation**: File type and size restrictions
- **Error Handling**: Structured logging without sensitive data

### Regulatory Compliance
- **Indian Banking Standards**: RBI-compliant assessment methodology
- **Data Privacy**: No external AI API calls for sensitive data
- **Audit Trail**: Complete logging of all decisions and calculations

## 🧪 Testing

### Unit Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Integration Tests
```bash
# Test document processing pipeline
curl -X POST "http://localhost:8000/api/ingest" \
  -F "files=@test.pdf" \
  -F "document_types=financial_statement"
```

### Health Checks
```bash
# Verify all services
curl http://localhost:8000/api/health
```

## 📈 Performance

### Processing Times
- **OCR Extraction**: ~2-5 minutes per document
- **Field Extraction**: ~30 seconds per document  
- **Cross-Validation**: ~1 minute
- **Five Cs Scoring**: ~30 seconds
- **CAM Generation**: ~3-5 minutes
- **Total Pipeline**: ~15-30 minutes

### System Requirements
- **Minimum**: 4 vCPU, 8GB RAM, 50GB SSD
- **Recommended**: 4 vCPU, 16GB RAM, 128GB SSD
- **Ollama Model**: gpt-oss (~13GB RAM required)

## 🔄 Deployment

### Production Setup
1. **SSL Configuration**: Let's Encrypt certificates at `/etc/letsencrypt/`
2. **Domain Setup**: DNS pointing to VM IP
3. **Ollama Service**: Ensure model is pulled and running
4. **Monitoring**: Set up log aggregation and health checks
5. **Backup Strategy**: Regular CAM document backups

### Scaling Considerations
- **Horizontal Scaling**: Multiple backend instances behind load balancer
- **Database**: Redis for job queue, PostgreSQL for persistence
- **File Storage**: S3 or similar for document/CAM storage
- **Caching**: Redis for API response caching

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Code review and merge

### Code Standards
- **Python**: PEP 8 compliance, type hints required
- **JavaScript**: ES6+ standards, JSDoc comments
- **CSS**: BEM methodology, mobile-first responsive design
- **Testing**: Minimum 80% test coverage required

## 📞 Support

### Documentation
- **API Documentation**: Available at `/docs` (Swagger UI)
- **User Guide**: Detailed operational procedures
- **Troubleshooting**: Common issues and solutions

### Monitoring
- **Application Logs**: `/tmp/intelli-credit.log`
- **Health Checks**: `/api/health` endpoint
- **Performance Metrics**: Request timing and error rates

## 📋 License

This project is proprietary to Vivriti Capital. All rights reserved.

---

**Built with ❤️ for India's MSME lending ecosystem**
