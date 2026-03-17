import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config import config
from shared.models import (
    FiveCScores, CreditGrade, ExtractedData, DocumentType,
    ValidationFlag, Severity, CreditDecision, FinancialFields,
    BankStatementFields, GSTFields, CIBILData
)

logger = logging.getLogger(__name__)

class FiveCSScorer:
    """Five Cs credit scoring engine with weighted calculations"""
    
    def __init__(self):
        self.weights = {
            'character': 0.25,
            'capacity': 0.30,
            'capital': 0.20,
            'collateral': 0.15,
            'conditions': 0.10
        }
        
        self.risk_thresholds = config.RISK_THRESHOLDS
    
    async def calculate_scores(
        self,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag],
        cibil_data: Optional[CIBILData] = None,
        sector: Optional[str] = None,
        research_findings: Optional[List[Dict[str, Any]]] = None
    ) -> FiveCScores:
        """
        Calculate Five Cs scores based on extracted data and external factors
        
        Args:
            extracted_data: List of extracted document data
            validation_flags: Cross-validation flags
            cibil_data: Credit bureau data
            sector: Business sector for conditions assessment
            research_findings: External research findings
            
        Returns:
            FiveCScores object with individual C scores
        """
        try:
            logger.info("Starting Five Cs scoring calculation")
            
            # Calculate individual C scores
            character_score = await self._calculate_character_score(
                validation_flags, cibil_data, research_findings
            )
            
            capacity_score = await self._calculate_capacity_score(
                extracted_data, validation_flags
            )
            
            capital_score = await self._calculate_capital_score(
                extracted_data, validation_flags
            )
            
            collateral_score = await self._calculate_collateral_score(
                extracted_data, validation_flags
            )
            
            conditions_score = await self._calculate_conditions_score(
                sector, validation_flags, research_findings
            )
            
            scores = FiveCScores(
                character=character_score,
                capacity=capacity_score,
                capital=capital_score,
                collateral=collateral_score,
                conditions=conditions_score
            )
            
            logger.info(f"Five Cs scoring completed - Total: {scores.get_weighted_score():.1f}")
            return scores
            
        except Exception as e:
            logger.error(f"Five Cs scoring failed: {e}")
            # Return minimum scores if calculation fails
            return FiveCScores(
                character=0.0, capacity=0.0, capital=0.0, 
                collateral=0.0, conditions=0.0
            )
    
    async def _calculate_character_score(
        self,
        validation_flags: List[ValidationFlag],
        cibil_data: Optional[CIBILData] = None,
        research_findings: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """Calculate Character score based on compliance and credit history"""
        try:
            base_score = 75.0  # Start with neutral score
            
            # Deductions from validation flags
            for flag in validation_flags:
                if flag.severity == Severity.CRITICAL:
                    base_score -= 25
                elif flag.severity == Severity.HIGH:
                    base_score -= 15
                elif flag.severity == Severity.MEDIUM:
                    base_score -= 8
                elif flag.severity == Severity.LOW:
                    base_score -= 3
            
            # CIBIL impact
            if cibil_data:
                if cibil_data.cmr_rank < 5:
                    base_score -= 20
                elif cibil_data.cmr_rank >= 8:
                    base_score += 10
                
                if cibil_data.overdue_amount > 0:
                    base_score -= 15
                
                if any(dpd.days_past_due > 30 for dpd in cibil_data.dpd_history_36m):
                    base_score -= 10
                
                if cibil_data.credit_enquiries_6m > 6:
                    base_score -= 8
            
            # Research findings impact
            if research_findings:
                for finding in research_findings:
                    if finding.get('severity') == 'CRITICAL':
                        base_score -= 20
                    elif finding.get('severity') == 'HIGH':
                        base_score -= 10
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            logger.error(f"Character score calculation failed: {e}")
            return 50.0
    
    async def _calculate_capacity_score(
        self,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag]
    ) -> float:
        """Calculate Capacity score based on cash flow and debt service"""
        try:
            base_score = 70.0
            
            # Get financial data
            financial_data = self._get_financial_data(extracted_data)
            
            if financial_data:
                # Calculate DSCR (Debt Service Coverage Ratio)
                if financial_data.ebitda_inr and financial_data.total_debt_inr:
                    # Assume 10% annual debt service for calculation
                    annual_debt_service = financial_data.total_debt_inr * 0.10
                    dscr = financial_data.ebitda_inr / annual_debt_service if annual_debt_service > 0 else 0
                    
                    # Score based on DSCR
                    if dscr >= 2.0:
                        base_score += 20
                    elif dscr >= 1.5:
                        base_score += 15
                    elif dscr >= 1.2:
                        base_score += 10
                    elif dscr >= 1.0:
                        base_score += 5
                    else:
                        base_score -= 15
                
                # Revenue growth trend (simplified)
                if financial_data.revenue_inr:
                    if financial_data.revenue_inr > 10000000:  # > 1 Cr
                        base_score += 10
                    elif financial_data.revenue_inr > 5000000:  # > 50 L
                        base_score += 5
            
            # Validation flags impact
            for flag in validation_flags:
                if flag.flag_type in ["REVENUE_INFLATION_RISK", "CASH_LEAKAGE_RISK"]:
                    if flag.severity == Severity.HIGH:
                        base_score -= 15
                    elif flag.severity == Severity.MEDIUM:
                        base_score -= 8
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            logger.error(f"Capacity score calculation failed: {e}")
            return 50.0
    
    async def _calculate_capital_score(
        self,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag]
    ) -> float:
        """Calculate Capital score based on net worth and financial stability"""
        try:
            base_score = 70.0
            
            financial_data = self._get_financial_data(extracted_data)
            
            if financial_data:
                # Net worth to total assets ratio
                if financial_data.net_worth_inr and financial_data.fixed_assets_inr:
                    total_assets = financial_data.net_worth_inr + financial_data.total_debt_inr if financial_data.total_debt_inr else financial_data.net_worth_inr
                    if total_assets > 0:
                        net_worth_ratio = financial_data.net_worth_inr / total_assets
                        if net_worth_ratio >= 0.4:
                            base_score += 15
                        elif net_worth_ratio >= 0.3:
                            base_score += 10
                        elif net_worth_ratio >= 0.2:
                            base_score += 5
                        else:
                            base_score -= 10
                
                # GST payment consistency
                gst_data = self._get_gst_data(extracted_data)
                if gst_data and gst_data.gstr3b_tax_paid_inr:
                    if gst_data.gstr3b_tax_paid_inr > 1000000:  # > 10 L tax paid
                        base_score += 10
            
            # Validation flags impact
            for flag in validation_flags:
                if flag.flag_type in ["GST_ITC_MISMATCH"]:
                    if flag.severity == Severity.HIGH:
                        base_score -= 12
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            logger.error(f"Capital score calculation failed: {e}")
            return 50.0
    
    async def _calculate_collateral_score(
        self,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag]
    ) -> float:
        """Calculate Collateral score based on asset quality and security"""
        try:
            base_score = 60.0
            
            # Get legal/collateral data
            legal_data = self._get_legal_data(extracted_data)
            financial_data = self._get_financial_data(extracted_data)
            
            if legal_data and legal_data.collateral_value_inr:
                if legal_data.collateral_value_inr > 50000000:  # > 5 Cr
                    base_score += 20
                elif legal_data.collateral_value_inr > 20000000:  # > 2 Cr
                    base_score += 15
                elif legal_data.collateral_value_inr > 10000000:  # > 1 Cr
                    base_score += 10
                elif legal_data.collateral_value_inr > 5000000:   # > 50 L
                    base_score += 5
                
                # Promoter guarantees
                if legal_data.promoter_guarantee_clauses:
                    base_score += len(legal_data.promoter_guarantee_clauses) * 2
            
            if financial_data and financial_data.fixed_assets_inr:
                if financial_data.fixed_assets_inr > 100000000:  # > 10 Cr
                    base_score += 15
                elif financial_data.fixed_assets_inr > 50000000:  # > 5 Cr
                    base_score += 10
                elif financial_data.fixed_assets_inr > 20000000:  # > 2 Cr
                    base_score += 5
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            logger.error(f"Collateral score calculation failed: {e}")
            return 50.0
    
    async def _calculate_conditions_score(
        self,
        sector: Optional[str],
        validation_flags: List[ValidationFlag],
        research_findings: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """Calculate Conditions score based on sector and external factors"""
        try:
            base_score = 75.0
            
            # Sector risk assessment
            if sector:
                sector_caps = config.SECTOR_CAPS
                if sector.upper() in sector_caps:
                    # Higher cap indicates lower sector risk
                    cap_value = sector_caps[sector.upper()]
                    if cap_value >= 500:  # NBFC
                        base_score += 5
                    elif cap_value >= 200:  # Manufacturing
                        base_score += 10
                    elif cap_value >= 150:  # Services
                        base_score += 8
                    else:  # Trading
                        base_score += 0
            
            # Research findings impact
            if research_findings:
                for finding in research_findings:
                    if finding.get('category') == 'regulatory':
                        if finding.get('severity') == 'HIGH':
                            base_score -= 15
                        elif finding.get('severity') == 'MEDIUM':
                            base_score -= 8
                    elif finding.get('category') == 'market':
                        if finding.get('severity') == 'HIGH':
                            base_score -= 10
                        elif finding.get('severity') == 'MEDIUM':
                            base_score -= 5
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            logger.error(f"Conditions score calculation failed: {e}")
            return 50.0
    
    def get_credit_grade(self, total_score: float) -> CreditGrade:
        """Get credit grade based on total weighted score"""
        if total_score >= self.risk_thresholds['LOW_RISK_MIN']:
            return CreditGrade.LOW_RISK
        elif total_score >= self.risk_thresholds['MODERATE_RISK_MIN']:
            return CreditGrade.MODERATE_RISK
        elif total_score >= self.risk_thresholds['HIGH_RISK_MIN']:
            return CreditGrade.HIGH_RISK
        else:
            return CreditGrade.DECLINE
    
    def _get_financial_data(self, extracted_data: List[ExtractedData]) -> Optional[FinancialFields]:
        """Extract financial data from extracted documents"""
        for data in extracted_data:
            if data.document_type == DocumentType.FINANCIAL_STATEMENT and data.financial_fields:
                return data.financial_fields
        return None
    
    def _get_gst_data(self, extracted_data: List[ExtractedData]) -> Optional[GSTFields]:
        """Extract GST data from extracted documents"""
        for data in extracted_data:
            if data.document_type == DocumentType.GST_RETURN and data.gst_fields:
                return data.gst_fields
        return None
    
    def _get_legal_data(self, extracted_data: List[ExtractedData]):
        """Extract legal/collateral data from extracted documents"""
        for data in extracted_data:
            if data.document_type == DocumentType.LEGAL_COLLATERAL and data.legal_fields:
                return data.legal_fields
        return None

# Global instance
five_cs_scorer = FiveCSScorer()
