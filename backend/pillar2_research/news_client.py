import logging
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime, timedelta

from config import config

logger = logging.getLogger(__name__)

class NewsClient:
    """News API client for company and promoter news analysis"""
    
    def __init__(self):
        self.api_key = config.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2"
        self.timeout = config.API_TIMEOUTS['NEWS_API']
        
        if not self.api_key:
            logger.warning("News API key not configured - using mock data")
            self.available = False
        else:
            self.available = True
    
    async def is_available(self) -> bool:
        """Check if News API service is available"""
        return self.available
    
    async def search_company_news(
        self,
        company_name: str,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Search for news about a specific company
        
        Args:
            company_name: Company name to search for
            days_back: Number of days to look back
            
        Returns:
            Dictionary with news articles and sentiment analysis
        """
        try:
            if not self.available:
                return await self._get_mock_news(company_name, "company")
            
            # Calculate date range
            from_date = datetime.now() - timedelta(days=days_back)
            to_date = datetime.now()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                search_url = f"{self.base_url}/everything"
                params = {
                    "q": f'"{company_name}"',
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat(),
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 50
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.get(search_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_news_response(data, "company")
                else:
                    logger.error(f"News API error: {response.status_code}")
                    return await self._get_mock_news(company_name, "company")
        
        except Exception as e:
            logger.error(f"Company news search failed: {e}")
            return await self._get_mock_news(company_name, "company")
    
    async def search_promoter_news(
        self,
        promoter_names: List[str],
        promoter_pans: List[str],
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Search for news about company promoters
        
        Args:
            promoter_names: List of promoter names
            promoter_pans: List of promoter PAN numbers
            days_back: Number of days to look back
            
        Returns:
            Dictionary with news articles and sentiment analysis
        """
        try:
            if not self.available:
                return await self._get_mock_news("promoters", "promoter")
            
            # Search for each promoter
            all_articles = []
            search_terms = []
            
            # Add names to search terms
            for name in promoter_names:
                search_terms.append(f'"{name}"')
            
            # Add PANs to search terms
            for pan in promoter_pans:
                search_terms.append(pan)
            
            # Search for each term
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for term in search_terms[:5]:  # Limit to avoid rate limits
                    search_url = f"{self.base_url}/everything"
                    params = {
                        "q": term,
                        "from": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "to": datetime.now().isoformat(),
                        "sortBy": "publishedAt",
                        "language": "en",
                        "pageSize": 20
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    response = await client.get(search_url, params=params, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                        all_articles.extend(articles)
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
            
            return self._parse_news_response({"articles": all_articles}, "promoter")
        
        except Exception as e:
            logger.error(f"Promoter news search failed: {e}")
            return await self._get_mock_news("promoters", "promoter")
    
    async def analyze_news_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze sentiment of news articles
        
        Args:
            articles: List of news articles
            
        Returns:
            Dictionary with sentiment analysis
        """
        try:
            if not articles:
                return {
                    "total_articles": 0,
                    "sentiment_score": 75.0,
                    "positive_articles": 0,
                    "negative_articles": 0,
                    "neutral_articles": 0,
                    "key_topics": []
                }
            
            # Simple sentiment analysis based on keywords
            positive_keywords = ["growth", "expansion", "profit", "success", "award", "partnership", "investment"]
            negative_keywords = ["loss", "debt", "lawsuit", "fraud", "scandal", "bankruptcy", "investigation", "regulatory"]
            
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            key_topics = []
            
            for article in articles:
                title = article.get("title", "").lower()
                description = article.get("description", "").lower()
                combined_text = f"{title} {description}"
                
                # Count sentiment indicators
                positive_score = sum(1 for keyword in positive_keywords if keyword in combined_text)
                negative_score = sum(1 for keyword in negative_keywords if keyword in combined_text)
                
                if positive_score > negative_score:
                    positive_count += 1
                elif negative_score > positive_score:
                    negative_count += 1
                else:
                    neutral_count += 1
                
                # Extract key topics
                if "business" in combined_text:
                    key_topics.append("business")
                if "financial" in combined_text:
                    key_topics.append("financial")
                if "legal" in combined_text:
                    key_topics.append("legal")
            
            # Calculate sentiment score
            total_articles = len(articles)
            if total_articles > 0:
                sentiment_score = ((positive_count - negative_count) / total_articles) * 50 + 50
            else:
                sentiment_score = 75.0
            
            return {
                "total_articles": total_articles,
                "sentiment_score": max(0, min(100, sentiment_score)),
                "positive_articles": positive_count,
                "negative_articles": negative_count,
                "neutral_articles": neutral_count,
                "key_topics": list(set(key_topics))
            }
        
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "total_articles": 0,
                "sentiment_score": 75.0,
                "positive_articles": 0,
                "negative_articles": 0,
                "neutral_articles": 0,
                "key_topics": []
            }
    
    def _parse_news_response(self, data: Dict[str, Any], search_type: str) -> Dict[str, Any]:
        """Parse News API response"""
        try:
            articles = data.get("articles", [])
            
            # Filter and process articles
            processed_articles = []
            for article in articles:
                processed_articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "author": article.get("author", "Unknown"),
                    "published_at": article.get("publishedAt", ""),
                    "url": article.get("url", ""),
                    "content": f"{article.get('title', '')} {article.get('description', '')}"
                })
            
            return {
                "search_type": search_type,
                "total_articles": len(processed_articles),
                "articles": processed_articles,
                "search_timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.warning(f"Failed to parse news response: {e}")
            return {
                "search_type": search_type,
                "total_articles": 0,
                "articles": [],
                "search_timestamp": datetime.now().isoformat()
            }
    
    async def _get_mock_news(self, entity_name: str, search_type: str) -> Dict[str, Any]:
        """Generate mock news data for testing"""
        import random
        from datetime import timedelta
        
        # Generate different mock scenarios based on search type and random chance
        scenarios = [
            {
                "total_articles": 0,
                "sentiment_score": 75.0,
                "description": "No recent news found"
            },
            {
                "total_articles": 2,
                "sentiment_score": 85.0,
                "description": "Positive business developments"
            },
            {
                "total_articles": 3,
                "sentiment_score": 45.0,
                "description": "Some negative press detected"
            },
            {
                "total_articles": 1,
                "sentiment_score": 30.0,
                "description": "Regulatory concerns identified"
            }
        ]
        
        scenario = random.choice(scenarios)
        
        # Generate mock articles based on scenario
        articles = []
        if scenario["total_articles"] > 0:
            for i in range(scenario["total_articles"]):
                published_date = datetime.now() - timedelta(days=random.randint(1, 90))
                
                if scenario["sentiment_score"] > 70:
                    title = f"{entity_name} Reports Strong Q{random.randint(1,4)} Results"
                    description = f"Company announces expansion plans and increased profitability"
                elif scenario["sentiment_score"] < 50:
                    title = f"Regulatory Scrutiny for {entity_name}"
                    description = f"Company faces investigation over compliance issues"
                else:
                    title = f"{entity_name} Maintains Steady Performance"
                    description = f"Company continues operations with mixed results"
                
                articles.append({
                    "title": title,
                    "description": description,
                    "source": random.choice(["Economic Times", "Business Standard", "Mint", "The Hindu"]),
                    "author": random.choice(["Staff Reporter", "Business Correspondent"]),
                    "published_at": published_date.isoformat(),
                    "url": f"https://example.com/news/{random.randint(1000, 9999)}",
                    "content": f"{title} {description}"
                })
        
        logger.info(f"Generated {len(articles)} mock news articles for {entity_name}")
        
        return {
            "search_type": search_type,
            "total_articles": len(articles),
            "articles": articles,
            "sentiment_score": scenario["sentiment_score"],
            "description": scenario["description"],
            "search_timestamp": datetime.now().isoformat()
        }

# Global instance
news_client = NewsClient()
