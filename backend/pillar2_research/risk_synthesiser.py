import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from shared.ollama_client import ollama_client
from shared.models import RiskFinding, Severity

logger = logging.getLogger(__name__)

class RiskSynthesiser:
    """Synthesise research findings into risk assessments using Ollama"""
    
    def __init__(self):
        self.synthesis_prompt = """You are a senior credit risk analyst synthesizing multiple research sources for a loan application.

Given the research data from different sources below, identify key risk factors and contradictions:

Company: {company_name}
CIN: {cin}

Research Data by Source:
{research_data}

Instructions:
1. Cross-reference findings across different sources
2. Identify contradictions or red flags
3. Look for patterns that indicate risk
4. Prioritize findings that would impact credit decision
5. For each significant finding, create a structured assessment

Risk Categories to Consider:
- Regulatory: Legal cases, compliance issues, regulatory violations
- Financial: Financial irregularities, cash flow problems, debt issues
- Operational: Management problems, operational inefficiencies
- Market: Industry challenges, competitive pressures, market risks
- Reputation: Negative publicity, management controversies

For each risk finding, provide:
- category: regulatory/financial/operational/market/reputation
- severity: LOW/MEDIUM/HIGH/CRITICAL (based on potential impact)
- description: Clear explanation of the risk and its implications
- source: Which data source revealed this information
- evidence: Specific data points supporting the finding

Return your analysis as a JSON array of risk findings. Focus on actionable insights that would influence a credit decision."""

        self.contradiction_prompt = """You are a senior credit analyst identifying contradictions in research data.

Company: {company_name}
CIN: {cin}

Research Data:
{research_data}

Instructions:
1. Compare information across different sources
2. Identify any contradictions, inconsistencies, or gaps
3. Highlight where information conflicts between sources
4. Flag areas where data is missing or unclear

Common contradictions to look for:
- Different financial figures across documents
- Conflicting compliance status
- Mismatched director information
- Inconsistent business operations data
- Discrepancies in legal status

For each contradiction found:
- category: Type of contradiction (financial/compliance/legal/operational)
- severity: How serious the contradiction is
- description: What conflicts were found
- conflicting_sources: Which sources disagree
- potential_impact: How this might affect credit assessment

Return as a JSON array of contradictions. Focus on material inconsistencies that could affect the lending decision."""

    async def synthesise_findings(
        self,
        company_name: str,
        cin: str,
        research_data: Dict[str, Any]
    ) -> List[RiskFinding]:
        """
        Synthesise research findings into structured risk assessments
        
        Args:
            company_name: Company name
            cin: Company Identification Number
            research_data: Raw research data from all sources
            
        Returns:
            List of RiskFinding objects
        """
        try:
            logger.info(f"Synthesising risk findings for {company_name}")
            
            # Format research data for synthesis
            formatted_data = self._format_research_data(research_data)
            
            # Generate synthesis prompt
            prompt = self.synthesis_prompt.format(
                company_name=company_name,
                cin=cin,
                research_data=formatted_data
            )
            
            # Get AI-powered synthesis
            findings_json = await ollama_client.extract_json(
                prompt=prompt,
                system="You are a senior credit risk analyst. Return structured JSON only."
            )
            
            # Convert to RiskFinding objects
            findings = []
            if isinstance(findings_json, list):
                for finding_data in findings_json:
                    try:
                        # Map severity
                        severity_map = {
                            "LOW": Severity.LOW,
                            "MEDIUM": Severity.MEDIUM,
                            "HIGH": Severity.HIGH,
                            "CRITICAL": Severity.CRITICAL
                        }
                        
                        finding = RiskFinding(
                            category=finding_data.get("category", "general"),
                            severity=severity_map.get(
                                finding_data.get("severity", "MEDIUM"),
                                Severity.MEDIUM
                            ),
                            description=finding_data.get("description", ""),
                            source=finding_data.get("source", "synthesis"),
                            raw_data=finding_data.get("evidence", {}),
                            detected_at=datetime.now()
                        )
                        findings.append(finding)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse risk finding: {e}")
                        continue
            
            logger.info(f"Synthesised {len(findings)} risk findings for {company_name}")
            return findings
            
        except Exception as e:
            logger.error(f"Risk synthesis failed: {e}")
            return []
    
    async def identify_contradictions(
        self,
        company_name: str,
        cin: str,
        research_data: Dict[str, Any]
    ) -> List[RiskFinding]:
        """
        Identify contradictions in research data
        
        Args:
            company_name: Company name
            cin: Company Identification Number
            research_data: Raw research data from all sources
            
        Returns:
            List of RiskFinding objects representing contradictions
        """
        try:
            logger.info(f"Identifying contradictions for {company_name}")
            
            # Format research data
            formatted_data = self._format_research_data(research_data)
            
            # Generate contradiction detection prompt
            prompt = self.contradiction_prompt.format(
                company_name=company_name,
                cin=cin,
                research_data=formatted_data
            )
            
            # Get AI-powered contradiction analysis
            contradictions_json = await ollama_client.extract_json(
                prompt=prompt,
                system="You are a senior credit analyst. Return structured JSON only."
            )
            
            # Convert contradictions to RiskFinding objects
            contradictions = []
            if isinstance(contradictions_json, list):
                for contradiction_data in contradictions_json:
                    try:
                        # Map severity based on potential impact
                        severity_map = {
                            "low": Severity.LOW,
                            "medium": Severity.MEDIUM,
                            "high": Severity.HIGH,
                            "critical": Severity.CRITICAL
                        }
                        
                        finding = RiskFinding(
                            category="data_contradiction",
                            severity=severity_map.get(
                                contradiction_data.get("severity", "medium"),
                                Severity.MEDIUM
                            ),
                            description=contradiction_data.get("description", ""),
                            source="data_contradiction_analysis",
                            raw_data=contradiction_data.get("conflicting_sources", {}),
                            detected_at=datetime.now()
                        )
                        contradictions.append(finding)
                        
                    except Exception as e:
                        logger.warning(f"Failed to parse contradiction: {e}")
                        continue
            
            logger.info(f"Identified {len(contradictions)} contradictions for {company_name}")
            return contradictions
            
        except Exception as e:
            logger.error(f"Contradiction identification failed: {e}")
            return []
    
    def _format_research_data(self, research_data: Dict[str, Any]) -> str:
        """Format research data for AI synthesis"""
        formatted_sections = []
        
        # Format each data source
        if research_data.get("ecourts_data"):
            formatted_sections.append("e-Courts Legal Data:")
            formatted_sections.append(str(research_data["ecourts_data"]))
        
        if research_data.get("mca21_directors"):
            formatted_sections.append("MCA21 Director Data:")
            for director in research_data["mca21_directors"]:
                formatted_sections.append(f"Director: {director.get('name', 'Unknown')} (DIN: {director.get('din', 'Unknown')})")
                formatted_sections.append(f"  - Active Directorships: {director.get('active_directorships', 0)}")
                formatted_sections.append(f"  - Struck Off Companies: {director.get('struck_off_companies', 0)}")
                formatted_sections.append(f"  - Compliance Score: {director.get('compliance_score', 0)}")
        
        if research_data.get("mca21_company"):
            formatted_sections.append("MCA21 Company Data:")
            company = research_data["mca21_company"]
            formatted_sections.append(f"Charges: {company.get('open_charges', 0)} open, {company.get('satisfied_charges', 0)} satisfied")
            formatted_sections.append(f"Annual Filings: {company.get('missing_filings', 0)} missing out of {company.get('total_filings', 0)} in last 3 years")
        
        if research_data.get("news_data"):
            formatted_sections.append("News Data:")
            news = research_data["news_data"]
            formatted_sections.append(f"Total Articles: {news.get('total_articles', 0)}")
            formatted_sections.append(f"Sentiment Score: {news.get('sentiment_score', 75)}/100")
            if news.get("negative_articles", 0) > 0:
                formatted_sections.append(f"Negative Articles: {news.get('negative_articles', 0)}")
        
        if research_data.get("rbi_data"):
            formatted_sections.append("RBI Regulatory Data:")
            rbi = research_data["rbi_data"]
            formatted_sections.append(f"Total Circulars: {rbi.get('total_circulars', 0)}")
            formatted_sections.append(f"Regulatory Alerts: {len(rbi.get('regulatory_alerts', []))}")
        
        return "\n\n".join(formatted_sections)
    
    async def generate_risk_summary(
        self,
        findings: List[RiskFinding]
    ) -> Dict[str, Any]:
        """
        Generate a summary of risk findings
        
        Args:
            findings: List of RiskFinding objects
            
        Returns:
            Dictionary with risk summary statistics
        """
        try:
            if not findings:
                return {
                    "total_findings": 0,
                    "severity_breakdown": {},
                    "category_breakdown": {},
                    "overall_risk_level": "LOW"
                }
            
            # Count by severity
            severity_counts = {
                "CRITICAL": 0,
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0
            }
            
            # Count by category
            category_counts = {}
            
            for finding in findings:
                # Count severity
                severity_counts[finding.severity.value] += 1
                
                # Count category
                category = finding.category
                if category not in category_counts:
                    category_counts[category] = 0
                category_counts[category] += 1
            
            # Determine overall risk level
            overall_risk_level = "LOW"
            if severity_counts["CRITICAL"] > 0:
                overall_risk_level = "CRITICAL"
            elif severity_counts["HIGH"] > 2:
                overall_risk_level = "HIGH"
            elif severity_counts["MEDIUM"] > 4:
                overall_risk_level = "MEDIUM"
            elif severity_counts["HIGH"] > 0 or severity_counts["MEDIUM"] > 2:
                overall_risk_level = "MODERATE"
            
            return {
                "total_findings": len(findings),
                "severity_breakdown": severity_counts,
                "category_breakdown": category_counts,
                "overall_risk_level": overall_risk_level,
                "generated_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Risk summary generation failed: {e}")
            return {
                "total_findings": 0,
                "severity_breakdown": {},
                "category_breakdown": {},
                "overall_risk_level": "UNKNOWN",
                "error": str(e)
            }

# Global instance
risk_synthesiser = RiskSynthesiser()
