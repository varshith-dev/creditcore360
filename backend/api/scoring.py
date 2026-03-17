from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from pillar3_engine.five_cs_scorer import five_cs_scorer
from pillar3_engine.loan_limit_calculator import loan_limit_calculator
from pillar3_engine.cibil_client import cibil_client
from pillar3_engine.cam_generator import cam_generator
from pillar3_engine.shap_explainer import shap_explainer
from shared.models import (
    DocumentType, CreditDecision, FiveCScores, CreditGrade,
    ExtractedData, ValidationFlag, CIBILData, LoanLimitResult, CAMDocument
)

logger = logging.getLogger(__name__)

scoring_router = APIRouter()

class ScoringRequest(BaseModel):
    company_name: str
    cin: str
    extracted_data: list[dict]  # List of ExtractedData as dicts
    validation_flags: list[dict] = []  # List of ValidationFlag as dicts
    research_data: Optional[dict] = None
    officer_observations: Optional[str] = None
    sector: Optional[str] = None

class ScoringResponse(BaseModel):
    status: str
    decision: Optional[dict] = None
    message: str

@scoring_router.post("/scoring/five-cs", response_model=ScoringResponse)
async def calculate_five_cs_scores(request: ScoringRequest):
    """Calculate Five Cs credit scores"""
    try:
        # Convert dicts back to Pydantic models
        extracted_data = [ExtractedData(**data) for data in request.extracted_data]
        validation_flags = [ValidationFlag(**flag) for flag in request.validation_flags]
        
        # Get CIBIL data
        cibil_data = await cibil_client.get_credit_report(company_cin=request.cin)
        
        # Calculate Five Cs scores
        five_c_scores = await five_cs_scorer.calculate_scores(
            extracted_data=extracted_data,
            validation_flags=validation_flags,
            cibil_data=cibil_data,
            sector=request.sector,
            research_findings=[request.research_data] if request.research_data else None
        )
        
        # Get credit grade
        total_score = five_c_scores.get_weighted_score()
        grade = five_cs_scorer.get_credit_grade(total_score)
        
        # Create credit decision
        decision = CreditDecision(
            company_name=request.company_name,
            cin=request.cin,
            five_c_scores=five_c_scores,
            total_score=total_score,
            grade=grade,
            cibil_data=cibil_data
        )
        
        return ScoringResponse(
            status="success",
            decision=decision.dict(),
            message="Five Cs scoring completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Five Cs scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@scoring_router.post("/scoring/loan-limit", response_model=ScoringResponse)
async def calculate_loan_limit(request: ScoringRequest):
    """Calculate loan limit based on three ceilings"""
    try:
        # Convert dicts back to Pydantic models
        extracted_data = [ExtractedData(**data) for data in request.extracted_data]
        
        # Calculate loan limit
        loan_limit = await loan_limit_calculator.calculate_loan_limit(
            extracted_data=extracted_data,
            sector=request.sector
        )
        
        # Get loan structuring suggestions
        suggestions = await loan_limit_calculator.get_loan_structuring_suggestions(
            extracted_data=extracted_data,
            sector=request.sector
        )
        
        return ScoringResponse(
            status="success",
            decision={
                "loan_limit": loan_limit.dict(),
                "suggestions": suggestions
            },
            message="Loan limit calculation completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Loan limit calculation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")

@scoring_router.post("/scoring/cam", response_model=ScoringResponse)
async def generate_cam(request: ScoringRequest):
    """Generate Credit Appraisal Memo (CAM)"""
    try:
        # Convert dicts back to Pydantic models
        extracted_data = [ExtractedData(**data) for data in request.extracted_data]
        validation_flags = [ValidationFlag(**flag) for flag in request.validation_flags]
        
        # Get CIBIL data
        cibil_data = await cibil_client.get_credit_report(company_cin=request.cin)
        
        # Calculate Five Cs scores
        five_c_scores = await five_cs_scorer.calculate_scores(
            extracted_data=extracted_data,
            validation_flags=validation_flags,
            cibil_data=cibil_data,
            sector=request.sector,
            research_findings=[request.research_data] if request.research_data else None
        )
        
        # Calculate loan limit
        loan_limit = await loan_limit_calculator.calculate_loan_limit(
            extracted_data=extracted_data,
            sector=request.sector
        )
        
        # Get loan structuring suggestions
        suggestions = await loan_limit_calculator.get_loan_structuring_suggestions(
            extracted_data=extracted_data,
            sector=request.sector
        )
        
        # Create credit decision
        total_score = five_c_scores.get_weighted_score()
        grade = five_cs_scorer.get_credit_grade(total_score)
        
        decision = CreditDecision(
            company_name=request.company_name,
            cin=request.cin,
            five_c_scores=five_c_scores,
            total_score=total_score,
            grade=grade,
            cibil_data=cibil_data,
            loan_limit=loan_limit,
            interest_rate_pct=suggestions.get("suggested_interest_rate_pct"),
            tenor_months=suggestions.get("suggested_tenor_months", 60)
        )
        
        # Generate SHAP explanation first
        shap_explanation = await shap_explainer.generate_explanation(
            credit_decision=decision,
            extracted_data=extracted_data,
            validation_flags=validation_flags
        )
        
        # Generate CAM with SHAP charts
        shap_chart_path = shap_explanation.get("charts", {}).get("summary_plot", "")
        
        cam_document = await cam_generator.generate_cam(
            credit_decision=decision,
            extracted_data=extracted_data,
            validation_flags=validation_flags,
            research_report=None,  # Will be implemented when research agent is ready
            officer_observations=request.officer_observations,
            shap_chart_path=shap_chart_path
        )
        
        return ScoringResponse(
            status="success",
            decision={
                "credit_decision": decision.dict(),
                "cam_document": cam_document.dict()
            },
            message="CAM generation completed successfully"
        )
        
    except Exception as e:
        logger.error(f"CAM generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@scoring_router.get("/scoring/grade/{score}")
async def get_credit_grade(score: float):
    """Get credit grade for a given score"""
    try:
        grade = five_cs_scorer.get_credit_grade(score)
        return {
            "score": score,
            "grade": grade.value,
            "thresholds": five_cs_scorer.risk_thresholds
        }
    except Exception as e:
        logger.error(f"Grade lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Grade lookup failed: {str(e)}")

@scoring_router.post("/scoring/explain")
async def explain_credit_decision(request: ScoringRequest):
    """Generate SHAP explanation for credit decision"""
    try:
        # Convert dicts back to Pydantic models
        extracted_data = [ExtractedData(**data) for data in request.extracted_data]
        validation_flags = [ValidationFlag(**flag) for flag in request.validation_flags]
        
        # Get credit decision first
        cibil_data = await cibil_client.get_credit_report(company_cin=request.cin)
        
        five_c_scores = await five_cs_scorer.calculate_scores(
            extracted_data=extracted_data,
            validation_flags=validation_flags,
            cibil_data=cibil_data,
            sector=request.sector,
            research_findings=[request.research_data] if request.research_data else None
        )
        
        total_score = five_c_scores.get_weighted_score()
        grade = five_cs_scorer.get_credit_grade(total_score)
        
        credit_decision = CreditDecision(
            company_name=request.company_name,
            cin=request.cin,
            five_c_scores=five_c_scores,
            total_score=total_score,
            grade=grade,
            cibil_data=cibil_data
        )
        
        # Generate SHAP explanation
        shap_explanation = await shap_explainer.generate_explanation(
            credit_decision=credit_decision,
            extracted_data=extracted_data,
            validation_flags=validation_flags
        )
        
        return {
            "status": "success",
            "credit_decision": credit_decision.dict(),
            "shap_explanation": shap_explanation,
            "message": "SHAP explanation generated successfully"
        }
        
    except Exception as e:
        logger.error(f"SHAP explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")

@scoring_router.get("/scoring/feature-importance")
async def get_feature_importance():
    """Get feature importance descriptions for SHAP"""
    try:
        feature_descriptions = {
            "financial_metrics": {
                "features": ["revenue_inr", "ebitda_inr", "pat_inr", "net_worth_inr", "total_debt_inr"],
                "description": "Key financial indicators from statements and ITR",
                "impact": "Directly affects Capacity and Capital scores"
            },
            "credit_indicators": {
                "features": ["cibil_cmr_rank", "cibil_overdue_inr", "cibil_enquiries_6m"],
                "description": "Credit bureau data affecting Character score",
                "impact": "Critical for creditworthiness assessment"
            },
            "operational_metrics": {
                "features": ["fixed_assets_inr", "cash_balance_inr", "gst_turnover_inr"],
                "description": "Operational efficiency and business health indicators",
                "impact": "Influences Capacity and Collateral assessment"
            },
            "risk_indicators": {
                "features": ["validation_flags_count", "sector_risk_score"],
                "description": "Cross-validation flags and sector-specific risks",
                "impact": "Affects Conditions and overall risk assessment"
            }
        }
        
        return {
            "status": "success",
            "feature_importance": feature_descriptions,
            "message": "Feature importance descriptions retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Feature importance lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve feature importance: {str(e)}")
