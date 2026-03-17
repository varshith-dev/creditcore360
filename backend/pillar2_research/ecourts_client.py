import logging
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

from config import config
from shared.models import CourtCase

logger = logging.getLogger(__name__)

class ECourtsClient:
    """e-Courts API client for legal case searches"""
    
    def __init__(self):
        self.api_key = config.ECOURTS_API_KEY
        self.base_url = "https://ecourts.gov.in"  # Example URL
        self.timeout = config.API_TIMEOUTS['ECOURTS']
        
        if not self.api_key:
            logger.warning("e-Courts API key not configured - using mock data")
            self.available = False
        else:
            self.available = True
    
    async def is_available(self) -> bool:
        """Check if e-Courts service is available"""
        return self.available
    
    async def search_cases_by_cin(self, cin: str) -> List[CourtCase]:
        """
        Search for pending court cases by Company Identification Number
        
        Args:
            cin: Company Identification Number
            
        Returns:
            List of CourtCase objects
        """
        try:
            if not self.available:
                return await self._get_mock_cases(cin)
            
            # In production, this would make actual API calls
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Search for cases by CIN
                search_url = f"{self.base_url}/api/cases/search"
                params = {
                    "cin": cin,
                    "case_type": "all",
                    "status": "pending"
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(search_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_court_cases(data.get("cases", []))
                else:
                    logger.error(f"e-Courts API error: {response.status_code}")
                    return await self._get_mock_cases(cin)
        
        except Exception as e:
            logger.error(f"e-Courts search failed: {e}")
            return await self._get_mock_cases(cin)
    
    async def search_cases_by_pan(self, pan: str) -> List[CourtCase]:
        """
        Search for court cases by promoter PAN number
        
        Args:
            pan: Permanent Account Number
            
        Returns:
            List of CourtCase objects
        """
        try:
            if not self.available:
                return await self._get_mock_cases_by_pan(pan)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                search_url = f"{self.base_url}/api/cases/search"
                params = {
                    "pan": pan,
                    "case_type": "all",
                    "status": "pending"
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(search_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_court_cases(data.get("cases", []))
                else:
                    logger.error(f"e-Courts API error: {response.status_code}")
                    return await self._get_mock_cases_by_pan(pan)
        
        except Exception as e:
            logger.error(f"e-Courts search failed: {e}")
            return await self._get_mock_cases_by_pan(pan)
    
    def _parse_court_cases(self, cases_data: List[Dict[str, Any]]) -> List[CourtCase]:
        """Parse API response into CourtCase objects"""
        court_cases = []
        
        for case_data in cases_data:
            try:
                # Parse case type and determine severity
                case_type = case_data.get("case_type", "").upper()
                severity = self._determine_case_severity(case_type)
                
                # Parse dates
                filing_date = None
                if case_data.get("filing_date"):
                    filing_date = datetime.fromisoformat(case_data["filing_date"])
                
                court_case = CourtCase(
                    case_number=case_data.get("case_number", ""),
                    case_type=case_type,
                    filing_date=filing_date,
                    current_status=case_data.get("current_status", "Unknown"),
                    court_name=case_data.get("court_name", "Unknown Court")
                )
                
                court_cases.append(court_case)
                
            except Exception as e:
                logger.warning(f"Failed to parse court case: {e}")
                continue
        
        return court_cases
    
    def _determine_case_severity(self, case_type: str) -> str:
        """Determine severity based on case type"""
        case_type_upper = case_type.upper()
        
        if "WINDING UP" in case_type_upper or "NCLT" in case_type_upper:
            return "CRITICAL"
        elif "DRT" in case_type_upper or "DEBT RECOVERY" in case_type_upper:
            return "HIGH"
        elif "SUIT" in case_type_upper or "COMPLAINT" in case_type_upper:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _get_mock_cases(self, cin: str) -> List[CourtCase]:
        """Generate mock court cases for testing"""
        import random
        
        # Simulate different scenarios based on CIN
        mock_cases = []
        
        # 70% chance of no cases
        if random.random() < 0.7:
            return mock_cases
        
        # Generate some mock cases
        num_cases = random.randint(1, 3)
        
        case_types = [
            ("CIVIL SUIT", "HIGH COURT MUMBAI", "2024-01-15"),
            ("RECOVERY SUIT", "DEBT RECOVERY TRIBUNAL", "2023-11-20"),
            ("COMPANY PETITION", "NCLT MUMBAI", "2024-02-10")
        ]
        
        for i in range(min(num_cases, len(case_types))):
            case_type, court_name, filing_date = case_types[i]
            
            mock_cases.append(CourtCase(
                case_number=f"2024/CIN/{cin}/SUITE/{i+1}",
                case_type=case_type,
                filing_date=datetime.fromisoformat(filing_date),
                current_status="Pending",
                court_name=court_name
            ))
        
        logger.info(f"Generated {len(mock_cases)} mock court cases for CIN: {cin}")
        return mock_cases
    
    async def _get_mock_cases_by_pan(self, pan: str) -> List[CourtCase]:
        """Generate mock court cases for PAN-based search"""
        import random
        
        # Similar to CIN-based but with PAN-specific logic
        mock_cases = []
        
        # 60% chance of no cases for individual PAN
        if random.random() < 0.6:
            return mock_cases
        
        # Generate mock case
        case_type = random.choice(["CIVIL SUIT", "RECOVERY SUIT"])
        court_name = random.choice(["HIGH COURT DELHI", "DISTRICT COURT BANGALORE"])
        
        mock_cases.append(CourtCase(
            case_number=f"2024/PAN/{pan}/SUITE/1",
            case_type=case_type,
            filing_date=datetime.now(),
            current_status="Pending",
            court_name=court_name
        ))
        
        logger.info(f"Generated mock court case for PAN: {pan}")
        return mock_cases
    
    async def get_case_details(self, case_number: str) -> Optional[CourtCase]:
        """
        Get detailed information about a specific case
        
        Args:
            case_number: Unique case identifier
            
        Returns:
            CourtCase object or None if not found
        """
        try:
            if not self.available:
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                detail_url = f"{self.base_url}/api/cases/{case_number}"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(detail_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    cases = self._parse_court_cases([data])
                    return cases[0] if cases else None
                else:
                    logger.error(f"Failed to get case details: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Failed to get case details: {e}")
            return None

# Global instance
ecourts_client = ECourtsClient()
