import logging
import asyncio
from typing import Optional, Dict, Any

from config import config
from shared.models import DocumentType, ExtractedData, FinancialFields, LoanLimitResult

logger = logging.getLogger(__name__)

class LoanLimitCalculator:
    """Calculate loan limits based on three independent ceilings"""
    
    def __init__(self):
        self.dscr_comfort_factor = config.DSCR_COMFORT_FACTOR
        self.loan_multiplier = config.LOAN_MULTIPLIER
        self.asset_leverage_ratio = config.ASSET_LEVERAGE_RATIO
    
    async def calculate_loan_limit(
        self,
        extracted_data: list[ExtractedData],
        sector: Optional[str] = None,
        proposed_tenor_months: int = 60  # Default 5 years
    ) -> LoanLimitResult:
        """
        Calculate loan limit based on three independent ceilings
        
        Args:
            extracted_data: List of extracted document data
            sector: Business sector for sector cap
            proposed_tenor_months: Proposed loan tenor in months
            
        Returns:
            LoanLimitResult with all three ceilings and final limit
        """
        try:
            logger.info("Starting loan limit calculation")
            
            # Calculate three independent ceilings
            cash_flow_ceiling = await self._calculate_cash_flow_ceiling(
                extracted_data, proposed_tenor_months
            )
            
            asset_ceiling = await self._calculate_asset_ceiling(extracted_data)
            
            sector_ceiling = await self._calculate_sector_ceiling(sector)
            
            # Final limit is the minimum of three ceilings
            final_limit = min(cash_flow_ceiling, asset_ceiling, sector_ceiling)
            
            # Determine which ceiling is binding
            if final_limit == cash_flow_ceiling:
                binding_ceiling = "cash_flow"
            elif final_limit == asset_ceiling:
                binding_ceiling = "asset_based"
            else:
                binding_ceiling = "sector_exposure"
            
            result = LoanLimitResult(
                final_limit_inr=final_limit,
                cash_flow_ceiling_inr=cash_flow_ceiling,
                asset_ceiling_inr=asset_ceiling,
                sector_ceiling_inr=sector_ceiling,
                binding_ceiling=binding_ceiling
            )
            
            logger.info(f"Loan limit calculated: ₹{final_limit/10000000:.2f} Cr (Binding: {binding_ceiling})")
            return result
            
        except Exception as e:
            logger.error(f"Loan limit calculation failed: {e}")
            # Return conservative limit if calculation fails
            return LoanLimitResult(
                final_limit_inr=10000000,  # ₹1 Cr default
                cash_flow_ceiling_inr=10000000,
                asset_ceiling_inr=10000000,
                sector_ceiling_inr=10000000,
                binding_ceiling="calculation_error"
            )
    
    async def _calculate_cash_flow_ceiling(
        self,
        extracted_data: list[ExtractedData],
        tenor_months: int
    ) -> float:
        """
        Calculate cash flow based ceiling using DSCR methodology
        
        Formula: 4 * DSCR_adjusted_free_cash_flow
        where DSCR_adjusted_fcf = avg_3yr_free_cash_flow * comfort_factor
        """
        try:
            financial_data = self._get_financial_data(extracted_data)
            if not financial_data or not financial_data.ebitda_inr:
                logger.warning("No EBITDA data available for cash flow ceiling")
                return 10000000  # ₹1 Cr default
            
            # Simplified calculation - in production, use 3-year average
            ebitda = financial_data.ebitda_inr
            
            # Estimate capex (15% of fixed assets) and taxes (25% of EBITDA)
            estimated_capex = 0
            if financial_data.fixed_assets_inr:
                estimated_capex = financial_data.fixed_assets_inr * 0.15
            
            estimated_taxes = ebitda * 0.25
            estimated_interest = 0
            if financial_data.total_debt_inr:
                # Assume 10% interest rate
                estimated_interest = financial_data.total_debt_inr * 0.10
            
            # Calculate free cash flow
            free_cash_flow = ebitda - estimated_capex - estimated_taxes - estimated_interest
            
            # Apply DSCR comfort factor
            dscr_adjusted_fcf = free_cash_flow * self.dscr_comfort_factor
            
            # Calculate ceiling (4x adjusted FCF)
            ceiling = dscr_adjusted_fcf * self.loan_multiplier
            
            logger.debug(f"Cash flow ceiling: ₹{ceiling/10000000:.2f} Cr")
            return max(0, ceiling)
            
        except Exception as e:
            logger.error(f"Cash flow ceiling calculation failed: {e}")
            return 10000000  # ₹1 Cr default
    
    async def _calculate_asset_ceiling(self, extracted_data: list[ExtractedData]) -> float:
        """
        Calculate asset based ceiling
        
        Formula: 0.60 * net_tangible_assets
        where net_tangible_assets = fixed_assets + net_current_assets - intangibles
        """
        try:
            financial_data = self._get_financial_data(extracted_data)
            if not financial_data:
                logger.warning("No financial data available for asset ceiling")
                return 15000000  # ₹1.5 Cr default
            
            # Calculate net tangible assets
            fixed_assets = financial_data.fixed_assets_inr or 0
            net_worth = financial_data.net_worth_inr or 0
            
            # Simplified: net current assets = net_worth - fixed_assets portion
            # In production, get this from balance sheet
            net_current_assets = max(0, net_worth - fixed_assets * 0.5)
            
            net_tangible_assets = fixed_assets + net_current_assets
            
            # Apply leverage ratio
            ceiling = net_tangible_assets * self.asset_leverage_ratio
            
            logger.debug(f"Asset ceiling: ₹{ceiling/10000000:.2f} Cr")
            return max(0, ceiling)
            
        except Exception as e:
            logger.error(f"Asset ceiling calculation failed: {e}")
            return 15000000  # ₹1.5 Cr default
    
    async def _calculate_sector_ceiling(self, sector: Optional[str]) -> float:
        """
        Calculate sector exposure cap
        
        Uses pre-configured sector caps in INR Crores
        """
        try:
            if not sector:
                logger.warning("No sector specified, using default cap")
                return 20000000  # ₹2 Cr default
            
            sector_cap_cr = config.get_sector_cap(sector)
            ceiling = sector_cap_cr * 10000000  # Convert Crores to INR
            
            logger.debug(f"Sector ceiling for {sector}: ₹{ceiling/10000000:.2f} Cr")
            return ceiling
            
        except Exception as e:
            logger.error(f"Sector ceiling calculation failed: {e}")
            return 20000000  # ₹2 Cr default
    
    def _get_financial_data(self, extracted_data: list[ExtractedData]) -> Optional[FinancialFields]:
        """Extract financial data from extracted documents"""
        for data in extracted_data:
            if data.document_type == DocumentType.FINANCIAL_STATEMENT and data.financial_fields:
                return data.financial_fields
        return None
    
    async def calculate_dscr(
        self,
        extracted_data: list[ExtractedData],
        proposed_loan_amount: float,
        interest_rate_pct: float = 10.0
    ) -> float:
        """
        Calculate Debt Service Coverage Ratio for proposed loan
        
        DSCR = EBITDA / (Interest + Principal Repayment)
        """
        try:
            financial_data = self._get_financial_data(extracted_data)
            if not financial_data or not financial_data.ebitda_inr:
                return 0.0
            
            ebitda = financial_data.ebitda_inr
            
            # Calculate annual debt service
            annual_interest = proposed_loan_amount * (interest_rate_pct / 100)
            annual_principal = proposed_loan_amount / 5  # Assume 5-year tenor
            annual_debt_service = annual_interest + annual_principal
            
            dscr = ebitda / annual_debt_service if annual_debt_service > 0 else 0
            
            logger.debug(f"DSCR: {dscr:.2f} (EBITDA: ₹{ebitda/100000:.2f} L, Debt Service: ₹{annual_debt_service/100000:.2f} L)")
            return dscr
            
        except Exception as e:
            logger.error(f"DSCR calculation failed: {e}")
            return 0.0
    
    async def get_loan_structuring_suggestions(
        self,
        extracted_data: list[ExtractedData],
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get loan structuring suggestions based on analysis
        """
        try:
            loan_limit = await self.calculate_loan_limit(extracted_data, sector)
            
            suggestions = {
                "max_loan_amount_inr": loan_limit.final_limit_inr,
                "binding_ceiling": loan_limit.binding_ceiling,
                "recommendations": []
            }
            
            # Add recommendations based on binding ceiling
            if loan_limit.binding_ceiling == "cash_flow":
                suggestions["recommendations"].append(
                    "Consider shorter tenor to improve DSCR"
                )
                suggestions["recommendations"].append(
                    "Monitor cash flow metrics closely"
                )
            elif loan_limit.binding_ceiling == "asset_based":
                suggestions["recommendations"].append(
                    "Consider additional collateral if available"
                )
                suggestions["recommendations"].append(
                    "Review asset valuation regularly"
                )
            elif loan_limit.binding_ceiling == "sector_exposure":
                suggestions["recommendations"].append(
                    "Sector exposure limit reached - consider syndication"
                )
                suggestions["recommendations"].append(
                    "Monitor sector risk indicators"
                )
            
            # Calculate suggested interest rate based on risk
            base_rate = 10.0  # Base rate
            if loan_limit.final_limit_inr < 10000000:  # < ₹1 Cr
                suggested_rate = base_rate + 2.0
            elif loan_limit.final_limit_inr < 50000000:  # < ₹5 Cr
                suggested_rate = base_rate + 1.0
            else:
                suggested_rate = base_rate
            
            suggestions["suggested_interest_rate_pct"] = suggested_rate
            suggestions["suggested_tenor_months"] = 60  # 5 years default
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Loan structuring suggestions failed: {e}")
            return {
                "max_loan_amount_inr": 10000000,
                "binding_ceiling": "error",
                "recommendations": ["Review calculation parameters"]
            }

# Global instance
loan_limit_calculator = LoanLimitCalculator()
