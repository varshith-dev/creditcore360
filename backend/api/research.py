from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from pillar2_research.agent_loop import research_agent
from pillar2_research.officer_portal import officer_portal_nlp
from shared.models import ResearchReport, FiveCScores

logger = logging.getLogger(__name__)

research_router = APIRouter()

class ResearchRequest(BaseModel):
    company_name: str
    cin: str
    promoter_pans: List[str] = []

class OfficerObservationsRequest(BaseModel):
    observations: str
    current_scores: Optional[dict] = None

@research_router.post("/research")
async def run_research(request: ResearchRequest):
    """Run research agent for company due diligence"""
    try:
        logger.info(f"Starting research for {request.company_name} ({request.cin})")
        
        # Run research agent
        research_report = await research_agent.run_research_agent(
            company_name=request.company_name,
            cin=request.cin,
            promoter_pans=request.promoter_pans
        )
        
        return {
            "status": "success",
            "research_report": research_report.dict(),
            "message": "Research completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Research agent failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

@research_router.post("/officer-observations")
async def process_officer_observations(request: OfficerObservationsRequest):
    """Process officer observations and adjust scores"""
    try:
        logger.info("Processing officer observations")
        
        # Convert current scores from dict if provided
        current_scores = None
        if request.current_scores:
            current_scores = FiveCScores(**request.current_scores)
        
        # Classify observations using NLP
        classification_result = await officer_portal_nlp.classify_observations(
            observations=request.observations,
            current_scores=current_scores
        )
        
        # Generate explanation for classification
        explanation = await officer_portal_nlp.explain_classification(
            observations=request.observations,
            detected_keywords=classification_result['detected_keywords']
        )
        
        return {
            "status": "success",
            "classification_result": classification_result,
            "explanation": explanation,
            "message": "Officer observations processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Officer observations processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@research_router.get("/research/keywords")
async def get_keyword_definitions():
    """Get definitions and impact descriptions for all keywords"""
    try:
        keyword_definitions = officer_portal_nlp.get_keyword_definitions()
        
        return {
            "status": "success",
            "keywords": keyword_definitions,
            "message": "Keyword definitions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get keyword definitions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve definitions: {str(e)}")

@research_router.post("/research/batch-classify")
async def batch_classify_observations(
    observations_list: List[str],
    current_scores_list: Optional[List[dict]] = None
):
    """Classify multiple observations in batch"""
    try:
        # Convert scores if provided
        scores_list = None
        if current_scores_list:
            scores_list = [FiveCScores(**scores) for scores in current_scores_list]
        
        # Process batch classification
        results = await officer_portal_nlp.batch_classify(
            observations_list=observations_list,
            current_scores_list=scores_list
        )
        
        return {
            "status": "success",
            "batch_results": results,
            "message": f"Batch classified {len(observations_list)} observations"
        }
        
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch classification failed: {str(e)}")

@research_router.get("/research/status")
async def get_research_status():
    """Get status of research components"""
    try:
        # Check availability of all research components
        ecourts_available = await research_agent.ecourts_client.is_available() if hasattr(research_agent, 'ecourts_client') else False
        mca21_available = await research_agent.mca21_client.is_available() if hasattr(research_agent, 'mca21_client') else False
        news_available = await research_agent.news_client.is_available() if hasattr(research_agent, 'news_client') else False
        
        nlp_initialized = officer_portal_nlp.classifier is not None
        
        return {
            "status": "success",
            "components": {
                "ecourts_api": {
                    "available": ecourts_available,
                    "status": "available" if ecourts_available else "unavailable"
                },
                "mca21_api": {
                    "available": mca21_available,
                    "status": "available" if mca21_available else "unavailable"
                },
                "news_api": {
                    "available": news_available,
                    "status": "available" if news_available else "unavailable"
                },
                "nlp_classifier": {
                    "available": nlp_initialized,
                    "status": "initialized" if nlp_initialized else "not_initialized"
                }
            },
            "message": "Research component status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get research status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
