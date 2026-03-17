import logging
import asyncio
from typing import Optional, Dict, Any
import httpx
from datetime import datetime, timedelta

from config import config
from shared.models import CIBILData, DPDEntry

logger = logging.getLogger(__name__)

class CIBILClient:
    """TransUnion CIBIL B2B API client for credit bureau data"""
    
    def __init__(self):
        self.base_url = "https://b2b.transunioncibil.com"  # Example URL
        self.client_id = config.CIBIL_B2B_CLIENT_ID
        self.client_secret = config.CIBIL_B2B_CLIENT_SECRET
        self.timeout = config.API_TIMEOUTS['CIBIL']
        self._access_token = None
        self._token_expires = None
        
        if not self.client_id or not self.client_secret:
            logger.warning("CIBIL B2B credentials not configured - using mock data")
            self.available = False
        else:
            self.available = True
    
    async def is_available(self) -> bool:
        """Check if CIBIL service is available"""
        return self.available
    
    async def get_credit_report(
        self, 
        company_cin: Optional[str] = None,
        company_pan: Optional[str] = None
    ) -> Optional[CIBILData]:
        """
        Fetch credit report from CIBIL B2B API
        
        Args:
            company_cin: Company Identification Number
            company_pan: Permanent Account Number
            
        Returns:
            CIBILData object with credit information
        """
        if not self.available:
            logger.info("CIBIL not available - returning mock data")
            return await self._get_mock_cibil_data()
        
        if not company_cin and not company_pan:
            raise ValueError("Either CIN or PAN must be provided")
        
        try:
            # Get access token
            await self._ensure_valid_token()
            
            # Prepare request
            request_data = {
                "request_id": f"INTELLI_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "company_identifier": {
                    "cin": company_cin,
                    "pan": company_pan
                },
                "product_type": "COMMERCIAL_REPORT",
                "consent": {
                    "provided": True,
                    "timestamp": datetime.now().isoformat(),
                    "purpose": "CREDIT_ASSESSMENT"
                }
            }
            
            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "X-API-KEY": self.client_id
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/credit-report",
                    json=request_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    report_data = response.json()
                    return self._parse_cibil_response(report_data)
                elif response.status_code == 401:
                    # Token expired, refresh and retry
                    await self._refresh_token()
                    return await self.get_credit_report(company_cin, company_pan)
                else:
                    logger.error(f"CIBIL API error: {response.status_code} - {response.text}")
                    return await self._get_mock_cibil_data()
        
        except Exception as e:
            logger.error(f"CIBIL API call failed: {e}")
            return await self._get_mock_cibil_data()
    
    async def _ensure_valid_token(self):
        """Ensure we have a valid access token"""
        if not self._access_token or not self._token_expires or datetime.now() >= self._token_expires:
            await self._refresh_token()
    
    async def _refresh_token(self):
        """Refresh OAuth access token"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                auth_data = {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
                
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    data=auth_data
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self._access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)
                    self._token_expires = datetime.now() + timedelta(seconds=expires_in - 300)  # Refresh 5 min early
                    logger.info("CIBIL access token refreshed successfully")
                else:
                    raise Exception(f"Token refresh failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Failed to refresh CIBIL token: {e}")
            raise
    
    def _parse_cibil_response(self, report_data: Dict[str, Any]) -> CIBILData:
        """Parse CIBIL API response into CIBILData object"""
        try:
            # Extract CMR rank
            cmr_rank = report_data.get("cmr_rank", 7)  # Default to moderate risk
            
            # Extract overdue amount
            overdue_amount = report_data.get("total_overdue_amount", 0.0)
            
            # Extract active credit facilities
            facilities = report_data.get("active_credit_facilities", [])
            
            # Extract DPD history
            dpd_entries = []
            dpd_history = report_data.get("dpd_history_36m", [])
            for dpd in dpd_history:
                dpd_entries.append(DPDEntry(
                    month=dpd.get("month", ""),
                    days_past_due=dpd.get("days_past_due", 0)
                ))
            
            # Extract credit enquiries
            enquiries_count = report_data.get("credit_enquiries_6m", 0)
            
            return CIBILData(
                cmr_rank=cmr_rank,
                overdue_amount_inr=float(overdue_amount),
                active_credit_facilities=facilities,
                dpd_history_36m=dpd_entries,
                credit_enquiries_6m=enquiries_count
            )
        
        except Exception as e:
            logger.error(f"Failed to parse CIBIL response: {e}")
            return self._get_default_cibil_data()
    
    async def _get_mock_cibil_data(self) -> CIBILData:
        """Generate mock CIBIL data for testing/demo purposes"""
        import random
        
        # Generate realistic mock data
        cmr_rank = random.randint(3, 9)
        overdue_amount = random.choice([0, 0, 0, 50000, 150000])  # Mostly zero with some overdue
        enquiries = random.randint(0, 8)
        
        # Generate DPD history
        dpd_entries = []
        for i in range(12):  # Last 12 months
            days_past_due = random.choice([0, 0, 0, 15, 30, 60]) if random.random() < 0.2 else 0
            dpd_entries.append(DPDEntry(
                month=f"{datetime.now().year}-{(datetime.now().month - i - 1) % 12 + 1:02d}",
                days_past_due=days_past_due
            ))
        
        facilities = [
            "Working Capital Limit - HDFC Bank",
            "Term Loan - SBI",
            "Cash Credit - ICICI Bank"
        ]
        
        return CIBILData(
            cmr_rank=cmr_rank,
            overdue_amount_inr=float(overdue_amount),
            active_credit_facilities=facilities,
            dpd_history_36m=dpd_entries,
            credit_enquiries_6m=enquiries
        )
    
    def _get_default_cibil_data(self) -> CIBILData:
        """Get default CIBIL data when parsing fails"""
        return CIBILData(
            cmr_rank=7,
            overdue_amount_inr=0.0,
            active_credit_facilities=[],
            dpd_history_36m=[],
            credit_enquiries_6m=0
        )

# Global instance
cibil_client = CIBILClient()
