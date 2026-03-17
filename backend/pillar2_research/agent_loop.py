import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from shared.ollama_client import ollama_client
from shared.models import ResearchReport, RiskFinding, Severity
from .ecourts_client import ecourts_client
from .mca21_client import mca21_client
from .news_client import news_client
from .rbi_feed_client import rbi_feed_client
from .risk_synthesiser import risk_synthesiser

logger = logging.getLogger(__name__)

class ResearchAgent:
    """Agentic research loop with plan-fetch-synthesize workflow"""
    
    def __init__(self):
        self.planning_prompt = """You are a senior credit research analyst planning due diligence for a corporate loan application.
Given the company information below, create a research plan with specific queries to run.

Company: {company_name}
CIN: {cin}
Promoter PANs: {promoter_pans}

Plan the following research areas:
1. e-Courts: Search for pending suits, winding up petitions, NCLT cases
2. MCA21: Check director profiles, charge registry, annual filings
3. News: Search for recent news about company and promoters
4. RBI: Check for regulatory circulars affecting the sector

For each area, specify:
- What to search for
- Why it's relevant for credit assessment
- Expected risk indicators to watch

Return your plan as a structured JSON with these areas clearly defined."""

        self.synthesis_prompt = """You are a senior credit analyst synthesizing research findings for a loan application.

Given the raw research data below, analyze and synthesize key risk findings:

Company: {company_name}
CIN: {cin}

Raw Research Data:
{raw_data}

Instructions:
1. Identify contradictions or red flags across different sources
2. For each significant finding, create a RiskFinding with:
   - category: regulatory/court/financial/operational/market
   - severity: LOW/MEDIUM/HIGH/CRITICAL
   - description: Clear explanation of the issue
   - source: Which data source revealed this
   - raw_data: Supporting evidence

3. Focus on findings that would impact credit decision
4. Be specific and cite actual data points
5. Return as a JSON array of RiskFinding objects

Only return valid JSON, no explanations or markdown."""

    async def run_research_agent(
        self,
        company_name: str,
        cin: str,
        promoter_pans: List[str]
    ) -> ResearchReport:
        """
        Run complete research agent loop: Plan → Fetch → Synthesise
        
        Args:
            company_name: Company name for research
            cin: Company Identification Number
            promoter_pans: List of promoter PAN numbers
            
        Returns:
            ResearchReport with findings and raw data
        """
        try:
            logger.info(f"Starting research agent for {company_name} ({cin})")
            
            # Step 1: PLAN - Create research plan using Ollama
            plan = await self._create_research_plan(company_name, cin, promoter_pans)
            
            # Step 2: FETCH - Execute research plan
            raw_data = await self._execute_research_plan(plan, company_name, cin, promoter_pans)
            
            # Step 3: SYNTHESISE - Analyze findings with Ollama
            findings = await risk_synthesiser.synthesise_findings(company_name, cin, raw_data)
            
            # Create research report
            report = ResearchReport(
                company_name=company_name,
                cin=cin,
                findings=findings,
                court_cases=raw_data.get("ecourts_cases", []),
                director_profiles=raw_data.get("mca21_directors", []),
                charge_registry=raw_data.get("mca21_company"),
                news_sentiment=raw_data.get("news_data", {}).get("sentiment_score", 75),
                rbi_alerts=raw_data.get("rbi_data", {}).get("regulatory_alerts", []),
                research_completed_at=datetime.now()
            )
            
            logger.info(f"Research agent completed for {company_name}: {len(findings)} findings")
            return report
            
        except Exception as e:
            logger.error(f"Research agent failed for {company_name}: {e}")
            # Return empty report on failure
            return ResearchReport(
                company_name=company_name,
                cin=cin,
                findings=[],
                research_completed_at=datetime.now()
            )
    
    async def _create_research_plan(
        self,
        company_name: str,
        cin: str,
        promoter_pans: List[str]
    ) -> Dict[str, Any]:
        """Create research plan using Ollama"""
        try:
            prompt = self.planning_prompt.format(
                company_name=company_name,
                cin=cin,
                promoter_pans=", ".join(promoter_pans)
            )
            
            plan_json = await ollama_client.extract_json(
                prompt=prompt,
                system="You are a senior credit research analyst. Return structured JSON only."
            )
            
            logger.info(f"Research plan created for {company_name}")
            return plan_json
            
        except Exception as e:
            logger.error(f"Failed to create research plan: {e}")
            return self._get_default_plan()
    
    async def _execute_research_plan(
        self,
        plan: Dict[str, Any],
        company_name: str,
        cin: str,
        promoter_pans: List[str]
    ) -> Dict[str, Any]:
        """Execute research plan by calling external APIs"""
        try:
            logger.info(f"Executing research plan for {company_name}")
            
            # Initialize results storage
            raw_data = {
                "plan": plan,
                "ecourts_cases": [],
                "mca21_directors": [],
                "mca21_company": None,
                "news_data": None,
                "rbi_data": None,
                "execution_timestamp": datetime.now().isoformat()
            }
            
            # Execute research concurrently
            tasks = []
            
            # Check if plan includes each research area
            research_areas = ["ecourts", "mca21", "news", "rbi"]
            
            if "ecourts" in plan:
                # Search cases by CIN and each PAN
                tasks.append(ecourts_client.search_cases_by_cin(cin))
                for pan in promoter_pans:
                    tasks.append(ecourts_client.search_cases_by_pan(pan))
            
            if "mca21" in plan:
                # Get director profiles and company data
                for pan in promoter_pans:
                    tasks.append(mca21_client.get_director_profile(self._pan_to_din(pan)))
                tasks.append(mca21_client.get_company_charge_registry(cin))
                tasks.append(mca21_client.check_annual_filings(cin, 3))
            
            if "news" in plan:
                # Search company and promoter news
                tasks.append(news_client.search_company_news(company_name))
                tasks.append(news_client.search_promoter_news([], promoter_pans))
            
            if "rbi" in plan:
                # Fetch RBI feeds (sector-specific if possible)
                tasks.append(rbi_feed_client.fetch_rbi_feeds())
            
            # Wait for all research tasks to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Research task {i} failed: {result}")
                        continue
                    
                    # Map results back to data sources
                    if i < len([r for r in research_areas if plan.get(r)]):
                        area = research_areas[i]
                        if area == "ecourts":
                            if isinstance(result, list):
                                raw_data["ecourts_cases"].extend(result)
                            else:
                                raw_data["ecourts_cases"].append(result)
                        elif area == "mca21":
                            if isinstance(result, list):
                                raw_data["mca21_directors"].extend(result)
                            else:
                                raw_data["mca21_company"] = result
                        elif area == "news":
                            raw_data["news_data"] = result
                        elif area == "rbi":
                            raw_data["rbi_data"] = result
            
            logger.info(f"Research execution completed for {company_name}")
            return raw_data
            
        except Exception as e:
            logger.error(f"Failed to execute research plan: {e}")
            return {"error": str(e), "execution_timestamp": datetime.now().isoformat()}
    
    def _pan_to_din(self, pan: str) -> str:
        """Convert PAN to DIN format for mock data"""
        return f"DIN{pan[:8].upper()}"
    
    def _get_default_plan(self) -> Dict[str, Any]:
        """Get default research plan when Ollama fails"""
        return {
            "ecourts": "Search for pending legal cases by CIN and PANs",
            "mca21": "Check director profiles and company filings",
            "news": "Search for recent news about company and promoters",
            "rbi": "Check RBI circulars affecting sector"
        }

# Global instance
research_agent = ResearchAgent()
