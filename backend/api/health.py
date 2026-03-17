from fastapi import APIRouter, HTTPException
import asyncio
import logging

from shared.ollama_client import ollama_client
from shared.models import JobInfo, JobStatus

logger = logging.getLogger(__name__)

health_router = APIRouter()

@health_router.get("/health")
async def detailed_health_check():
    """Detailed health check including all services"""
    try:
        # Check Ollama
        ollama_status = await ollama_client.health_check()
        
        # Check system resources
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "ok",
            "services": {
                "ollama": {
                    "status": "reachable" if ollama_status else "unreachable",
                    "model": ollama_client.model,
                    "endpoint": ollama_client.base_url
                }
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@health_router.get("/health/ollama")
async def ollama_health():
    """Check Ollama service specifically"""
    try:
        is_healthy = await ollama_client.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "model": ollama_client.model,
            "endpoint": ollama_client.base_url
        }
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {str(e)}")
