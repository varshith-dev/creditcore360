import logging
import asyncio
from typing import List, Dict, Any, Optional
import httpx
import feedparser
from datetime import datetime, timedelta

from config import config

logger = logging.getLogger(__name__)

class RBIFeedClient:
    """RBI RSS feed client for regulatory circulars and alerts"""
    
    def __init__(self):
        self.rss_url = "https://www.rbi.org.in/rss.aspx"
        self.timeout = config.API_TIMEOUTS['RBI_FEED']
        self.sector_keywords = {
            "NBFC": ["nbfc", "non-banking financial", "microfinance", "gold loan"],
            "MANUFACTURING": ["manufacturing", "production", "industry", "factory"],
            "TRADING": ["trading", "commodity", "exports", "imports"],
            "SERVICES": ["services", "it", "software", "consulting", "bpo"],
            "TEXTILES": ["textile", "garments", "apparel", "cotton"],
            "PHARMACEUTICALS": ["pharma", "drugs", "pharmaceutical", "medicine"],
            "REAL_ESTATE": ["real estate", "housing", "construction", "infrastructure"],
            "BANKING": ["banking", "bank", "credit", "loan", "interest rates"]
        }
    
    async def fetch_rbi_feeds(self, sector: Optional[str] = None, days_back: int = 30) -> Dict[str, Any]:
        """
        Fetch RBI RSS feeds and filter for sector-specific circulars
        
        Args:
            sector: Business sector to focus on
            days_back: Number of days to look back
            
        Returns:
            Dictionary with RBI circulars and alerts
        """
        try:
            logger.info(f"Fetching RBI feeds for sector: {sector}")
            
            # Fetch RSS feed
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.rss_url)
                if response.status_code == 200:
                    feed_content = response.text
                    feed = feedparser.parse(feed_content)
                    return self._parse_rbi_feed(feed, sector, days_back)
                else:
                    logger.error(f"Failed to fetch RBI RSS feed: {response.status_code}")
                    return await self._get_mock_rbi_feed(sector)
        
        except Exception as e:
            logger.error(f"RBI feed fetch failed: {e}")
            return await self._get_mock_rbi_feed(sector)
    
    def _parse_rbi_feed(self, feed, sector: Optional[str], days_back: int) -> Dict[str, Any]:
        """Parse RBI RSS feed and filter for relevant circulars"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            circulars = []
            regulatory_alerts = []
            
            for entry in feed.entries:
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published'):
                    pub_date = entry.published
                elif hasattr(entry, 'updated'):
                    pub_date = entry.updated
                
                if not pub_date:
                    continue
                
                # Skip old entries
                if pub_date < cutoff_date:
                    continue
                
                # Parse entry data
                title = entry.title.lower()
                summary = entry.summary.lower() if hasattr(entry, 'summary') else ""
                content = f"{title} {summary}"
                
                # Determine if this is relevant to the sector
                relevance_score = self._calculate_sector_relevance(content, sector)
                
                circular_data = {
                    "title": entry.title,
                    "summary": entry.summary if hasattr(entry, 'summary') else "",
                    "link": entry.link if hasattr(entry, 'link') else "",
                    "published_date": pub_date.isoformat(),
                    "category": self._categorize_circular(title, summary),
                    "relevance_score": relevance_score,
                    "sector": sector
                }
                
                # Classify as regulatory alert or general circular
                if relevance_score >= 0.7 or self._is_regulatory_alert(title, summary):
                    regulatory_alerts.append(circular_data)
                else:
                    circulars.append(circular_data)
            
            return {
                "sector": sector,
                "total_circulars": len(circulars) + len(regulatory_alerts),
                "regulatory_alerts": regulatory_alerts,
                "general_circulars": circulars,
                "fetch_timestamp": datetime.now().isoformat(),
                "days_analyzed": days_back
            }
        
        except Exception as e:
            logger.error(f"Failed to parse RBI feed: {e}")
            return {
                "sector": sector,
                "total_circulars": 0,
                "regulatory_alerts": [],
                "general_circulars": [],
                "fetch_timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _calculate_sector_relevance(self, content: str, sector: Optional[str]) -> float:
        """Calculate relevance score for a sector"""
        if not sector:
            return 0.5  # Neutral relevance if no sector specified
        
        sector_upper = sector.upper()
        if sector_upper not in self.sector_keywords:
            return 0.3  # Low relevance for unknown sectors
        
        keywords = self.sector_keywords[sector_upper]
        relevance_score = 0.0
        
        # Count keyword matches
        for keyword in keywords:
            if keyword in content:
                relevance_score += 1.0
        
        # Normalize score
        max_possible_score = len(keywords)
        if max_possible_score > 0:
            relevance_score = min(1.0, relevance_score / max_possible_score)
        
        return relevance_score
    
    def _categorize_circular(self, title: str, summary: str) -> str:
        """Categorize RBI circular type"""
        content = f"{title.lower()} {summary.lower()}"
        
        # Priority-based categorization
        if any(word in content for word in ["master direction", "regulation", "guidelines", "framework"]):
            return "Regulatory"
        elif any(word in content for word in ["interest rate", "repo rate", "monetary policy", "inflation"]):
            return "Monetary Policy"
        elif any(word in content for word in ["banking", "nbfc", "cooperative", "payment"]):
            return "Banking"
        elif any(word in content for word in ["foreign exchange", "forex", "external trade"]):
            return "Forex"
        elif any(word in content for word in ["financial inclusion", "priority sector", "msme"]):
            return "Financial Inclusion"
        elif any(word in content for word in ["supervision", "compliance", "enforcement"]):
            return "Supervision"
        else:
            return "General"
    
    def _is_regulatory_alert(self, title: str, summary: str) -> bool:
        """Check if circular is a regulatory alert"""
        content = f"{title.lower()} {summary.lower()}"
        
        alert_keywords = [
            "urgent", "immediate", "alert", "warning", "restriction", "ban", "prohibition",
            "compliance action", "penalty", "suspension", "revocation", "closure"
        ]
        
        return any(keyword in content for keyword in alert_keywords)
    
    async def _get_mock_rbi_feed(self, sector: Optional[str]) -> Dict[str, Any]:
        """Generate mock RBI feed data for testing"""
        import random
        from datetime import timedelta
        
        # Generate mock circulars
        circulars = []
        regulatory_alerts = []
        
        # Generate 5-10 mock circulars
        num_circulars = random.randint(5, 10)
        
        for i in range(num_circulars):
            pub_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            # Generate different types of circulars
            circular_types = [
                ("Regulatory", "Updated KYC Guidelines for NBFCs"),
                ("Monetary Policy", "Repo Rate Adjustment"),
                ("Banking", "Priority Sector Lending Rates"),
                ("Financial Inclusion", "MSME Loan Restructuring Framework"),
                ("Supervision", "Annual Supervision Calendar")
            ]
            
            circular_type, title = random.choice(circular_types)
            
            # Make some circulars regulatory alerts
            is_alert = random.random() < 0.2  # 20% chance of alert
            
            circular_data = {
                "title": title,
                "summary": f"Details about {title.lower()} implementation and compliance requirements.",
                "link": f"https://rbi.org.in/scripts/BS_ViewBS.aspx?Id={random.randint(1000, 9999)}",
                "published_date": pub_date.isoformat(),
                "category": circular_type,
                "relevance_score": random.uniform(0.5, 1.0),
                "sector": sector
            }
            
            if is_alert:
                regulatory_alerts.append(circular_data)
            else:
                circulars.append(circular_data)
        
        logger.info(f"Generated {len(circulars)} mock RBI circulars for sector: {sector}")
        
        return {
            "sector": sector,
            "total_circulars": len(circulars) + len(regulatory_alerts),
            "regulatory_alerts": regulatory_alerts,
            "general_circulars": circulars,
            "fetch_timestamp": datetime.now().isoformat(),
            "mock_data": True
        }
    
    async def get_circular_details(self, circular_url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific RBI circular
        
        Args:
            circular_url: URL to the RBI circular
            
        Returns:
            Dictionary with circular details or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(circular_url)
                
                if response.status_code == 200:
                    # Parse HTML content to extract details
                    content = response.text
                    return self._parse_circular_details(content, circular_url)
                else:
                    logger.error(f"Failed to fetch circular details: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Failed to get circular details: {e}")
            return None
    
    def _parse_circular_details(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse HTML content of RBI circular"""
        try:
            # Simple HTML parsing to extract key information
            # In production, this would use proper HTML parsing library
            
            # Extract title
            title_start = html_content.find("<title>")
            title_end = html_content.find("</title>")
            title = html_content[title_start + 7:title_end] if title_start != -1 and title_end != -1 else "Unknown Title"
            
            # Extract publication date
            date_patterns = [
                "Date:", "Published on:", "Issue Date:", "Release Date:"
            ]
            
            pub_date = None
            for pattern in date_patterns:
                pattern_start = html_content.find(pattern)
                if pattern_start != -1:
                    # Extract date after the pattern
                    date_start = pattern_start + len(pattern)
                    date_end = html_content.find("<", date_start)
                    if date_end != -1:
                        date_str = html_content[date_start:date_end].strip()
                        # Try to parse date
                        pub_date = self._parse_date_string(date_str)
                    break
            
            return {
                "url": url,
                "title": title,
                "publication_date": pub_date,
                "content_length": len(html_content),
                "parsed_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.warning(f"Failed to parse circular details: {e}")
            return {
                "url": url,
                "title": "Parse Error",
                "publication_date": None,
                "content_length": 0,
                "error": str(e)
            }
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from RBI circulars"""
        date_formats = [
            "%d-%m-%Y",
            "%d/%m/%Y", 
            "%B %d, %Y",
            "%d %B %Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None

# Global instance
rbi_feed_client = RBIFeedClient()
