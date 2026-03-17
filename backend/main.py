import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from config import config
from shared.ollama_client import ollama_client
from shared.models import JobInfo, JobStatus
from api.health import health_router
from api.ingest import ingest_router
from api.research import research_router
from api.scoring import scoring_router
from api.jobs import jobs_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/intelli-credit.log')
    ]
)

logger = logging.getLogger(__name__)

# In-memory job store (for production, use Redis or database)
job_store: dict[str, JobInfo] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Intelli-Credit backend...")
    
    # Validate configuration
    if not config.validate_config():
        logger.error("Configuration validation failed")
        raise RuntimeError("Invalid configuration")
    
    # Check Ollama availability
    ollama_available = await ollama_client.health_check()
    if ollama_available:
        logger.info("Ollama is reachable and model is available")
    else:
        logger.warning("Ollama is not reachable - AI features will be limited")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Intelli-Credit backend...")
    await ollama_client.close()

# Create FastAPI app
app = FastAPI(
    title="Intelli-Credit API",
    description="AI-Powered Corporate Credit Appraisal Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Include API routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(ingest_router, prefix="/api", tags=["ingest"])
app.include_router(research_router, prefix="/api", tags=["research"])
app.include_router(scoring_router, prefix="/api", tags=["scoring"])
app.include_router(jobs_router, prefix="/api", tags=["jobs"])

# Frontend routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - redirect to upload"""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Document upload page"""
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/portal", response_class=HTMLResponse)
async def officer_portal(request: Request):
    """Officer portal page"""
    return templates.TemplateResponse("officer_portal.html", {"request": request})

@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """Results dashboard page"""
    return templates.TemplateResponse("results.html", {"request": request})

@app.get("/preview", response_class=HTMLResponse)
async def cam_preview(request: Request):
    """CAM preview page"""
    return templates.TemplateResponse("cam_preview.html", {"request": request})

# API endpoints
@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Intelli-Credit API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "ingest": "/api/ingest",
            "research": "/api/research",
            "scoring": "/api/scoring",
            "jobs": "/api/jobs"
        }
    }

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        ollama_status = await ollama_client.health_check()
        return {
            "status": "ok",
            "ollama": "reachable" if ollama_status else "unreachable",
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

def get_job_store() -> dict[str, JobInfo]:
    """Get the global job store"""
    return job_store

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=config.LOG_LEVEL.lower()
    )
