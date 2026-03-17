import logging
import asyncio
from typing import Dict, Any, Optional

from shared.ollama_client import ollama_client
from shared.models import (
    DocumentType, FinancialFields, BankStatementFields, GSTFields, 
    ITRFields, LegalCollateralFields, ExtractedData
)

logger = logging.getLogger(__name__)

class FieldExtractor:
    """Extract structured fields from document text using Ollama"""
    
    def __init__(self):
        self.extraction_prompts = self._initialize_prompts()
    
    def _initialize_prompts(self) -> Dict[DocumentType, Dict[str, Any]]:
        """Initialize extraction prompts and schemas for each document type"""
        return {
            DocumentType.FINANCIAL_STATEMENT: {
                "system_prompt": """You are a financial document analyst extracting key financial metrics from Indian corporate financial statements. 
Extract ONLY the numerical values that are explicitly stated in the document. 
If a value is not found, use null. Do not hallucinate or estimate values.
All monetary values should be in INR (Indian Rupees).""",
                "schema": {
                    "revenue_inr": "Total revenue/sales turnover in INR",
                    "ebitda_inr": "EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization) in INR",
                    "pat_inr": "Profit After Tax in INR",
                    "net_worth_inr": "Net worth/shareholders' equity in INR",
                    "total_debt_inr": "Total borrowings/debt in INR",
                    "fixed_assets_inr": "Fixed assets/Gross block in INR",
                    "financial_year": "Financial year (e.g., '2022-23')"
                }
            },
            
            DocumentType.BANK_STATEMENT: {
                "system_prompt": """You are a banking analyst extracting key metrics from corporate bank statements.
Extract ONLY values that are explicitly visible in the statement. 
If a value is not found, use null. Do not calculate or estimate.
All monetary values should be in INR (Indian Rupees).""",
                "schema": {
                    "avg_monthly_balance_inr": "Average monthly balance in INR",
                    "total_credits_inr": "Total credits/deposits in the period in INR",
                    "total_debits_inr": "Total debits/withdrawals in the period in INR",
                    "large_cash_withdrawals_inr": "Total large cash withdrawals (>₹50,000) in INR",
                    "bounce_count": "Number of cheque/transaction bounces",
                    "emi_obligations_inr": "Total EMI/auto-debit obligations in INR"
                }
            },
            
            DocumentType.GST_RETURN: {
                "system_prompt": """You are a GST specialist extracting key figures from GST returns (GSTR-3B, GSTR-2A).
Extract ONLY values that are explicitly stated in the return documents.
If a value is not found, use null. Do not calculate or estimate.
All monetary values should be in INR (Indian Rupees).""",
                "schema": {
                    "gstr3b_annual_turnover_inr": "Annual turnover as per GSTR-3B in INR",
                    "gstr2a_itc_claimed_inr": "Total ITC claimed as per GSTR-2A in INR",
                    "gstr3b_tax_paid_inr": "Total tax paid as per GSTR-3B in INR"
                }
            },
            
            DocumentType.ITR: {
                "system_prompt": """You are a tax analyst extracting key information from Income Tax Returns (ITR) of Indian companies.
Extract ONLY information that is explicitly stated in the ITR document.
If a value is not found, use null. Do not calculate or estimate.
All monetary values should be in INR (Indian Rupees).""",
                "schema": {
                    "itr_declared_income_inr": "Total income declared in ITR in INR",
                    "itr_year": "Assessment year (e.g., '2022-23')",
                    "source_of_income": "Primary source of income (business/profession/capital gains/etc.)"
                }
            },
            
            DocumentType.LEGAL_COLLATERAL: {
                "system_prompt": """You are a legal analyst extracting key information from legal documents, loan agreements, and collateral documents.
Extract ONLY information that is explicitly stated in the document.
If information is not found, use null. Do not estimate or assume.
All monetary values should be in INR (Indian Rupees).""",
                "schema": {
                    "collateral_description": "Description of collateral offered",
                    "collateral_value_inr": "Value of collateral in INR",
                    "promoter_guarantee_clauses": "List of promoter guarantee clauses (array of strings)",
                    "contingent_liabilities_inr": "Contingent liabilities in INR"
                }
            }
        }
    
    async def extract_fields(
        self, 
        document_text: str, 
        document_type: DocumentType
    ) -> ExtractedData:
        """
        Extract structured fields from document text
        
        Args:
            document_text: Extracted text from OCR/document
            document_type: Type of document being processed
            
        Returns:
            ExtractedData with structured fields
        """
        try:
            prompt_config = self.extraction_prompts.get(document_type)
            if not prompt_config:
                raise ValueError(f"Unsupported document type: {document_type}")
            
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(
                document_text, 
                prompt_config["schema"]
            )
            
            # Extract fields using Ollama
            extracted_json = await ollama_client.extract_json(
                prompt=extraction_prompt,
                system=prompt_config["system_prompt"]
            )
            
            # Parse and validate extracted data
            structured_data = await self._parse_extracted_data(
                extracted_json, 
                document_type
            )
            
            # Calculate extraction confidence
            confidence = self._calculate_confidence(extracted_json, document_text)
            
            return ExtractedData(
                document_type=document_type,
                financial_fields=structured_data.get("financial_fields"),
                bank_fields=structured_data.get("bank_fields"),
                gst_fields=structured_data.get("gst_fields"),
                itr_fields=structured_data.get("itr_fields"),
                legal_fields=structured_data.get("legal_fields"),
                validation_flags=[],  # Will be populated by cross_validator
                extraction_confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Field extraction failed for {document_type}: {e}")
            # Return empty extraction with low confidence
            return ExtractedData(
                document_type=document_type,
                extraction_confidence=0.0,
                validation_flags=[]
            )
    
    def _build_extraction_prompt(self, document_text: str, schema: Dict[str, str]) -> str:
        """Build extraction prompt with document text and field descriptions"""
        prompt = f"""Extract the following fields from the provided document text:

Document Text:
{document_text[:8000]}  # Limit to first 8K chars to avoid context limits

Fields to extract:
"""
        for field_name, description in schema.items():
            prompt += f"- {field_name}: {description}\n"
        
        prompt += """
IMPORTANT:
- Return ONLY a valid JSON object with these exact field names
- Use null for any field that cannot be found in the document
- Do not include any explanations or text outside the JSON
- Extract exact values as written in the document (do not calculate or estimate)
- For monetary values, extract only the number (no currency symbols or commas)
"""
        return prompt
    
    async def _parse_extracted_data(
        self, 
        extracted_json: Dict[str, Any], 
        document_type: DocumentType
    ) -> Dict[str, Any]:
        """Parse and validate extracted JSON into typed Pydantic models"""
        result = {}
        
        try:
            if document_type == DocumentType.FINANCIAL_STATEMENT:
                result["financial_fields"] = FinancialFields(**extracted_json)
            elif document_type == DocumentType.BANK_STATEMENT:
                result["bank_fields"] = BankStatementFields(**extracted_json)
            elif document_type == DocumentType.GST_RETURN:
                result["gst_fields"] = GSTFields(**extracted_json)
            elif document_type == DocumentType.ITR:
                result["itr_fields"] = ITRFields(**extracted_json)
            elif document_type == DocumentType.LEGAL_COLLATERAL:
                result["legal_fields"] = LegalCollateralFields(**extracted_json)
                
        except Exception as e:
            logger.warning(f"Failed to parse extracted data: {e}")
            # Return empty fields for this document type
            if document_type == DocumentType.FINANCIAL_STATEMENT:
                result["financial_fields"] = FinancialFields()
            elif document_type == DocumentType.BANK_STATEMENT:
                result["bank_fields"] = BankStatementFields()
            elif document_type == DocumentType.GST_RETURN:
                result["gst_fields"] = GSTFields()
            elif document_type == DocumentType.ITR:
                result["itr_fields"] = ITRFields()
            elif document_type == DocumentType.LEGAL_COLLATERAL:
                result["legal_fields"] = LegalCollateralFields()
        
        return result
    
    def _calculate_confidence(self, extracted_json: Dict[str, Any], document_text: str) -> float:
        """Calculate confidence score based on extraction completeness"""
        if not extracted_json:
            return 0.0
        
        # Count non-null fields
        total_fields = len(extracted_json)
        non_null_fields = sum(1 for value in extracted_json.values() if value is not None and value != "")
        
        if total_fields == 0:
            return 0.0
        
        # Base confidence from field completeness
        completeness_score = non_null_fields / total_fields
        
        # Adjust based on document text length (longer documents might have more data)
        text_length_factor = min(1.0, len(document_text) / 2000)  # Normalize to 2K chars
        
        # Final confidence score
        confidence = completeness_score * 0.8 + text_length_factor * 0.2
        
        return round(confidence, 2)

# Global instance
field_extractor = FieldExtractor()
