import logging
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime

from config import config
from shared.models import DirectorProfile, ChargeRegistry

logger = logging.getLogger(__name__)

class MCA21Client:
    """MCA21 API client for corporate registry data"""
    
    def __init__(self):
        self.api_key = config.MCA21_API_KEY
        self.base_url = "https://www.mca.gov.in"  # Example URL
        self.timeout = config.API_TIMEOUTS['MCA21']
        
        if not self.api_key:
            logger.warning("MCA21 API key not configured - using mock data")
            self.available = False
        else:
            self.available = True
    
    async def is_available(self) -> bool:
        """Check if MCA21 service is available"""
        return self.available
    
    async def get_director_profile(self, din: str) -> Optional[DirectorProfile]:
        """
        Get director profile by Director Identification Number
        
        Args:
            din: Director Identification Number
            
        Returns:
            DirectorProfile object or None if not found
        """
        try:
            if not self.available:
                return await self._get_mock_director_profile(din)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                profile_url = f"{self.base_url}/api/directors/{din}"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(profile_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_director_profile(data)
                else:
                    logger.error(f"MCA21 API error: {response.status_code}")
                    return await self._get_mock_director_profile(din)
        
        except Exception as e:
            logger.error(f"MCA21 director profile fetch failed: {e}")
            return await self._get_mock_director_profile(din)
    
    async def get_director_profiles_by_pans(self, pans: List[str]) -> List[DirectorProfile]:
        """
        Get multiple director profiles by PAN numbers
        
        Args:
            pans: List of Permanent Account Numbers
            
        Returns:
            List of DirectorProfile objects
        """
        try:
            profiles = []
            
            # Fetch profiles concurrently
            tasks = [
                self.get_director_profile(self._pan_to_din(pan))
                for pan in pans
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Director profile fetch failed: {result}")
                    continue
                
                if result:
                    profiles.append(result)
            
            return profiles
        
        except Exception as e:
            logger.error(f"Failed to fetch director profiles: {e}")
            return []
    
    async def get_company_charge_registry(self, cin: str) -> Optional[ChargeRegistry]:
        """
        Get charge registry for a company
        
        Args:
            cin: Company Identification Number
            
        Returns:
            ChargeRegistry object or None if not found
        """
        try:
            if not self.available:
                return await self._get_mock_charge_registry(cin)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                charges_url = f"{self.base_url}/api/companies/{cin}/charges"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(charges_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_charge_registry(data)
                else:
                    logger.error(f"MCA21 charges API error: {response.status_code}")
                    return await self._get_mock_charge_registry(cin)
        
        except Exception as e:
            logger.error(f"MCA21 charge registry fetch failed: {e}")
            return await self._get_mock_charge_registry(cin)
    
    async def check_annual_filings(self, cin: str, years: int = 3) -> Dict[str, Any]:
        """
        Check annual filing compliance for a company
        
        Args:
            cin: Company Identification Number
            years: Number of years to check back
            
        Returns:
            Dictionary with filing compliance information
        """
        try:
            if not self.available:
                return await self._get_mock_filings(cin, years)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                filings_url = f"{self.base_url}/api/companies/{cin}/filings"
                params = {"years": years}
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(filings_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_filings_data(data)
                else:
                    logger.error(f"MCA21 filings API error: {response.status_code}")
                    return await self._get_mock_filings(cin, years)
        
        except Exception as e:
            logger.error(f"MCA21 filings check failed: {e}")
            return await self._get_mock_filings(cin, years)
    
    def _parse_director_profile(self, data: Dict[str, Any]) -> DirectorProfile:
        """Parse API response into DirectorProfile object"""
        try:
            return DirectorProfile(
                din=data.get("din", ""),
                name=data.get("name", ""),
                active_directorships=data.get("active_directorships", 0),
                resigned_directorships=data.get("resigned_directorships", 0),
                struck_off_companies=data.get("struck_off_companies", 0),
                compliance_score=data.get("compliance_score", 0.0)
            )
        except Exception as e:
            logger.warning(f"Failed to parse director profile: {e}")
            return DirectorProfile(
                din=data.get("din", ""),
                name="Unknown",
                active_directorships=0,
                resigned_directorships=0,
                struck_off_companies=0,
                compliance_score=0.0
            )
    
    def _parse_charge_registry(self, data: Dict[str, Any]) -> ChargeRegistry:
        """Parse API response into ChargeRegistry object"""
        try:
            latest_charge_date = None
            if data.get("latest_charge_date"):
                latest_charge_date = datetime.fromisoformat(data["latest_charge_date"])
            
            return ChargeRegistry(
                total_charges=data.get("total_charges", 0),
                open_charges=data.get("open_charges", 0),
                satisfied_charges=data.get("satisfied_charges", 0),
                latest_charge_date=latest_charge_date
            )
        except Exception as e:
            logger.warning(f"Failed to parse charge registry: {e}")
            return ChargeRegistry(
                total_charges=0,
                open_charges=0,
                satisfied_charges=0,
                latest_charge_date=None
            )
    
    def _parse_filings_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse annual filings data"""
        try:
            return {
                "years_checked": data.get("years_checked", 0),
                "total_filings": data.get("total_filings", 0),
                "missing_filings": data.get("missing_filings", 0),
                "compliance_percentage": data.get("compliance_percentage", 100.0),
                "last_filing_date": data.get("last_filing_date"),
                "filings_summary": data.get("filings_summary", [])
            }
        except Exception as e:
            logger.warning(f"Failed to parse filings data: {e}")
            return {
                "years_checked": 0,
                "total_filings": 0,
                "missing_filings": 0,
                "compliance_percentage": 0.0,
                "last_filing_date": None,
                "filings_summary": []
            }
    
    def _pan_to_din(self, pan: str) -> str:
        """Convert PAN to DIN format for mock data"""
        # Simple conversion for mock purposes
        return f"DIN{pan[:8].upper()}"
    
    async def _get_mock_director_profile(self, din: str) -> DirectorProfile:
        """Generate mock director profile for testing"""
        import random
        
        # Generate realistic mock data
        active_directorships = random.randint(1, 5)
        resigned_directorships = random.randint(0, 3)
        struck_off_companies = random.randint(0, 2)
        
        # Calculate compliance score based on risk factors
        compliance_score = 100.0
        if struck_off_companies > 0:
            compliance_score -= struck_off_companies * 10
        if active_directorships > 8:
            compliance_score -= 20
        if resigned_directorships > 5:
            compliance_score -= 15
        
        compliance_score = max(0, min(100, compliance_score))
        
        return DirectorProfile(
            din=din,
            name=f"Director {din[-4:]}",
            active_directorships=active_directorships,
            resigned_directorships=resigned_directorships,
            struck_off_companies=struck_off_companies,
            compliance_score=compliance_score
        )
    
    async def _get_mock_charge_registry(self, cin: str) -> ChargeRegistry:
        """Generate mock charge registry for testing"""
        import random
        
        total_charges = random.randint(0, 10)
        open_charges = random.randint(0, total_charges)
        satisfied_charges = total_charges - open_charges
        
        latest_charge_date = datetime.now()
        if total_charges == 0:
            latest_charge_date = None
        
        return ChargeRegistry(
            total_charges=total_charges,
            open_charges=open_charges,
            satisfied_charges=satisfied_charges,
            latest_charge_date=latest_charge_date
        )
    
    async def _get_mock_filings(self, cin: str, years: int) -> Dict[str, Any]:
        """Generate mock annual filings data for testing"""
        import random
        from datetime import timedelta
        
        total_filings = years * 4  # Assume 4 filings per year
        missing_filings = random.randint(0, 2)
        compliance_percentage = ((total_filings - missing_filings) / total_filings) * 100
        
        last_filing_date = datetime.now() - timedelta(days=random.randint(30, 180))
        
        filings_summary = []
        for year in range(datetime.now().year - years + 1, datetime.now().year + 1):
            for i in range(4):
                filings_summary.append({
                    "year": year,
                    "filing_type": random.choice(["Annual Return", "Financial Statement", "Director Report"]),
                    "filing_date": f"{year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                    "status": "Filed" if random.random() > 0.1 else "Missing"
                })
        
        return {
            "years_checked": years,
            "total_filings": total_filings,
            "missing_filings": missing_filings,
            "compliance_percentage": compliance_percentage,
            "last_filing_date": last_filing_date.isoformat(),
            "filings_summary": filings_summary
        }

# Global instance
mca21_client = MCA21Client()
