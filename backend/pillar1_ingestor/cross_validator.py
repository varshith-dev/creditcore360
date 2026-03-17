import logging
import asyncio
from typing import List, Dict, Any, Optional
import networkx as nx

from config import config
from shared.models import (
    ValidationFlag, Severity, ExtractedData, DocumentType,
    FinancialFields, BankStatementFields, GSTFields, ITRFields
)

logger = logging.getLogger(__name__)

class CrossValidator:
    """Perform 5 cross-validation checks on extracted data"""
    
    def __init__(self):
        self.thresholds = {
            'gst_itc_mismatch': config.GST_ITC_MISMATCH_THRESHOLD,
            'revenue_inflation': config.REVENUE_INFLATION_THRESHOLD,
            'headcount_variance': config.HEADCOUNT_VARIANCE_THRESHOLD,
            'cash_leakage': config.CASH_LEAKAGE_THRESHOLD
        }
    
    async def validate_documents(self, extracted_data: List[ExtractedData]) -> List[ValidationFlag]:
        """
        Perform all 5 cross-validation checks concurrently
        
        Args:
            extracted_data: List of extracted data from all documents
            
        Returns:
            List of validation flags from all checks
        """
        try:
            # Organize data by document type
            data_by_type = self._organize_by_type(extracted_data)
            
            # Run all validation checks concurrently
            checks = [
                self._check_gst_itc_mismatch(data_by_type),
                self._check_revenue_inflation(data_by_type),
                self._check_tds_vs_headcount(data_by_type),
                self._check_cash_withdrawals_vs_opex(data_by_type),
                self._check_circular_trading(data_by_type)
            ]
            
            results = await asyncio.gather(*checks, return_exceptions=True)
            
            # Collect all validation flags
            all_flags = []
            for result in results:
                if isinstance(result, list):
                    all_flags.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Validation check failed: {result}")
            
            logger.info(f"Cross-validation completed: {len(all_flags)} flags generated")
            return all_flags
            
        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return []
    
    def _organize_by_type(self, extracted_data: List[ExtractedData]) -> Dict[DocumentType, ExtractedData]:
        """Organize extracted data by document type"""
        data_by_type = {}
        for data in extracted_data:
            data_by_type[data.document_type] = data
        return data_by_type
    
    async def _check_gst_itc_mismatch(self, data_by_type: Dict[DocumentType, ExtractedData]) -> List[ValidationFlag]:
        """Check 1: GSTR-2A vs GSTR-3B ITC delta"""
        flags = []
        
        try:
            gst_data = data_by_type.get(DocumentType.GST_RETURN)
            if not gst_data or not gst_data.gst_fields:
                return flags
            
            gst_fields = gst_data.gst_fields
            
            if (gst_fields.gstr2a_itc_claimed_inr and gst_fields.gstr3b_tax_paid_inr and 
                gst_fields.gstr3b_tax_paid_inr > 0):
                
                # Calculate mismatch ratio
                mismatch_ratio = abs(gst_fields.gstr2a_itc_claimed_inr - gst_fields.gstr3b_tax_paid_inr) / gst_fields.gstr3b_tax_paid_inr
                
                if mismatch_ratio > self.thresholds['gst_itc_mismatch']:
                    flags.append(ValidationFlag(
                        flag_type="GST_ITC_MISMATCH",
                        severity=Severity.HIGH,
                        description=f"GSTR-2A ITC ({gst_fields.gstr2a_itc_claimed_inr:,.0f}) differs from GSTR-3B tax paid ({gst_fields.gstr3b_tax_paid_inr:,.0f}) by {mismatch_ratio:.1%}",
                        affected_fields=["gstr2a_itc_claimed_inr", "gstr3b_tax_paid_inr"],
                        raw_values={
                            "gstr2a_itc_claimed_inr": gst_fields.gstr2a_itc_claimed_inr,
                            "gstr3b_tax_paid_inr": gst_fields.gstr3b_tax_paid_inr,
                            "mismatch_ratio": mismatch_ratio
                        }
                    ))
        
        except Exception as e:
            logger.error(f"GST ITC mismatch check failed: {e}")
        
        return flags
    
    async def _check_revenue_inflation(self, data_by_type: Dict[DocumentType, ExtractedData]) -> List[ValidationFlag]:
        """Check 2: ITR income vs GST turnover"""
        flags = []
        
        try:
            itr_data = data_by_type.get(DocumentType.ITR)
            gst_data = data_by_type.get(DocumentType.GST_RETURN)
            
            if not itr_data or not itr_data.itr_fields or not gst_data or not gst_data.gst_fields:
                return flags
            
            itr_fields = itr_data.itr_fields
            gst_fields = gst_data.gst_fields
            
            if (itr_fields.itr_declared_income_inr and gst_fields.gstr3b_annual_turnover_inr and 
                gst_fields.gstr3b_annual_turnover_inr > 0):
                
                # Calculate variance ratio
                variance_ratio = abs(itr_fields.itr_declared_income_inr - gst_fields.gstr3b_annual_turnover_inr) / gst_fields.gstr3b_annual_turnover_inr
                
                if variance_ratio > self.thresholds['revenue_inflation']:
                    flags.append(ValidationFlag(
                        flag_type="REVENUE_INFLATION_RISK",
                        severity=Severity.HIGH,
                        description=f"ITR income ({itr_fields.itr_declared_income_inr:,.0f}) differs from GST turnover ({gst_fields.gstr3b_annual_turnover_inr:,.0f}) by {variance_ratio:.1%}",
                        affected_fields=["itr_declared_income_inr", "gstr3b_annual_turnover_inr"],
                        raw_values={
                            "itr_declared_income_inr": itr_fields.itr_declared_income_inr,
                            "gstr3b_annual_turnover_inr": gst_fields.gstr3b_annual_turnover_inr,
                            "variance_ratio": variance_ratio
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Revenue inflation check failed: {e}")
        
        return flags
    
    async def _check_tds_vs_headcount(self, data_by_type: Dict[DocumentType, ExtractedData]) -> List[ValidationFlag]:
        """Check 3: TDS filings vs headcount"""
        flags = []
        
        try:
            # This check would require additional data sources (TDS filings, declared headcount)
            # For now, we'll implement a placeholder that can be enhanced with real data
            
            financial_data = data_by_type.get(DocumentType.FINANCIAL_STATEMENT)
            if not financial_data or not financial_data.financial_fields:
                return flags
            
            # Placeholder logic - in real implementation, this would:
            # 1. Fetch TDS filings by PAN
            # 2. Compare implied headcount from TDS vs declared headcount
            # 3. Flag if variance > 40%
            
            # For demonstration, we'll skip this check or mark as pending data
            logger.info("TDS vs headcount check skipped - requires external TDS data")
        
        except Exception as e:
            logger.error(f"TDS vs headcount check failed: {e}")
        
        return flags
    
    async def _check_cash_withdrawals_vs_opex(self, data_by_type: Dict[DocumentType, ExtractedData]) -> List[ValidationFlag]:
        """Check 4: Bank withdrawals vs declared opex"""
        flags = []
        
        try:
            bank_data = data_by_type.get(DocumentType.BANK_STATEMENT)
            financial_data = data_by_type.get(DocumentType.FINANCIAL_STATEMENT)
            
            if not bank_data or not bank_data.bank_fields or not financial_data or not financial_data.financial_fields:
                return flags
            
            bank_fields = bank_data.bank_fields
            financial_fields = financial_data.financial_fields
            
            if bank_fields.large_cash_withdrawals_inr and financial_fields.ebitda_inr:
                # Use EBITDA as proxy for operating expenses
                cash_ratio = bank_fields.large_cash_withdrawals_inr / financial_fields.ebitda_inr
                
                if cash_ratio > self.thresholds['cash_leakage']:
                    flags.append(ValidationFlag(
                        flag_type="CASH_LEAKAGE_RISK",
                        severity=Severity.MEDIUM,
                        description=f"Large cash withdrawals ({bank_fields.large_cash_withdrawals_inr:,.0f}) exceed 30% of EBITDA ({financial_fields.ebitda_inr:,.0f})",
                        affected_fields=["large_cash_withdrawals_inr", "ebitda_inr"],
                        raw_values={
                            "large_cash_withdrawals_inr": bank_fields.large_cash_withdrawals_inr,
                            "ebitda_inr": financial_fields.ebitda_inr,
                            "cash_ratio": cash_ratio
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Cash withdrawal vs opex check failed: {e}")
        
        return flags
    
    async def _check_circular_trading(self, data_by_type: Dict[DocumentType, ExtractedData]) -> List[ValidationFlag]:
        """Check 5: Circular trading detection using NetworkX"""
        flags = []
        
        try:
            # This check would require GST invoice data with supplier/receiver GST numbers
            # For now, we'll implement a placeholder that can be enhanced with real GST data
            
            gst_data = data_by_type.get(DocumentType.GST_RETURN)
            if not gst_data or not gst_data.gst_fields:
                return flags
            
            # Placeholder logic - in real implementation, this would:
            # 1. Build directed graph from GST invoice data
            # 2. Nodes = GST numbers, edges = invoices
            # 3. Detect circular patterns within 30 days
            # 4. Flag suspicious circular trading
            
            logger.info("Circular trading check skipped - requires detailed GST invoice data")
        
        except Exception as e:
            logger.error(f"Circular trading check failed: {e}")
        
        return flags
    
    async def _detect_circular_patterns(self, invoice_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect circular trading patterns using NetworkX"""
        try:
            # Build directed graph
            G = nx.DiGraph()
            
            # Add nodes and edges from invoice data
            for invoice in invoice_data:
                supplier_gst = invoice.get('supplier_gst')
                receiver_gst = invoice.get('receiver_gst')
                invoice_date = invoice.get('invoice_date')
                invoice_amount = invoice.get('amount', 0)
                
                if supplier_gst and receiver_gst:
                    G.add_edge(supplier_gst, receiver_gst, 
                              date=invoice_date, amount=invoice_amount)
            
            # Find strongly connected components (potential circular trading)
            circular_components = []
            for component in nx.strongly_connected_components(G):
                if len(component) > 1:  # Only consider components with multiple nodes
                    # Check if transactions within 30 days
                    subgraph = G.subgraph(component)
                    circular_components.append({
                        'nodes': list(component),
                        'edges': list(subgraph.edges(data=True))
                    })
            
            return circular_components
        
        except Exception as e:
            logger.error(f"Circular pattern detection failed: {e}")
            return []

# Global instance
cross_validator = CrossValidator()
