import logging
import asyncio
from typing import List, Dict, Any, Optional
from transformers import pipeline, AutoTokenizer
import torch

from config import config
from shared.models import FiveCScores

logger = logging.getLogger(__name__)

class OfficerPortalNLP:
    """NLP classifier for officer observations using DistilBERT"""
    
    def __init__(self):
        self.model_name = config.DISTILBERT_MODEL
        self.device = -1  # Force CPU inference as per constraints
        self.classifier = None
        self.score_adjustments = config.SCORE_ADJUSTMENTS
        
        # Risk keywords for classification
        self.risk_keywords = {
            'idle_machinery': ['idle machinery', 'unused equipment', 'machinery not running', 'plant shutdown'],
            'capacity_underutilised': ['underutilised', 'low capacity', 'not running at full', 'excess capacity'],
            'promoter_absent': ['promoter absent', 'management not available', 'no promoter', 'management missing'],
            'overdue_creditors': ['overdue creditors', 'pending payments', 'delayed payments', 'supplier dues'],
            'working_capital_stress': ['working capital issues', 'cash flow problems', 'liquidity crisis', 'fund shortage'],
            'strong_management': ['strong management', 'experienced team', 'competent management', 'good leadership'],
            'modern_facility': ['modern facility', 'new equipment', 'state of the art', 'advanced machinery'],
            'clean_premises': ['clean premises', 'well maintained', 'good housekeeping', 'organized workplace']
        }
    
    async def initialize(self):
        """Initialize the NLP classifier"""
        try:
            logger.info(f"Initializing NLP classifier with model: {self.model_name}")
            
            # Initialize zero-shot classifier
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=self.device
            )
            
            # Candidate labels for classification
            self.candidate_labels = list(self.risk_keywords.keys())
            
            logger.info("NLP classifier initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP classifier: {e}")
            return False
    
    async def classify_observations(
        self,
        observations: str,
        current_scores: Optional[FiveCScores] = None
    ) -> Dict[str, Any]:
        """
        Classify officer observations and calculate score adjustments
        
        Args:
            observations: Free-text observations from officer
            current_scores: Current Five Cs scores
            
        Returns:
            Dictionary with classification results and score adjustments
        """
        try:
            if not self.classifier:
                await self.initialize()
            
            logger.info("Classifying officer observations")
            
            # Preprocess observations
            processed_text = self._preprocess_text(observations)
            
            # Perform zero-shot classification
            classification_results = self.classifier(
                processed_text,
                candidate_labels=self.candidate_labels,
                hypothesis_template="This example is {}."
            )
            
            # Extract classifications and scores
            detected_keywords = []
            score_adjustments = {c: 0 for c in ['character', 'capacity', 'capital', 'collateral', 'conditions']}
            
            for i, (sequence, scores) in enumerate(zip(classification_results['labels'], classification_results['scores'])):
                if scores > 0.5:  # Confidence threshold
                    keyword = sequence
                    detected_keywords.append(keyword)
                    
                    # Apply score adjustments
                    if keyword in self.score_adjustments:
                        adjustments = self.score_adjustments[keyword]
                        for category, adjustment in adjustments.items():
                            score_adjustments[category] += adjustment
            
            # Calculate adjustment summary
            total_adjustment = sum(abs(adj) for adj in score_adjustments.values())
            
            # Apply adjustments to current scores if provided
            adjusted_scores = None
            if current_scores:
                adjusted_scores = FiveCScores(
                    character=max(0, min(100, current_scores.character + score_adjustments['character'])),
                    capacity=max(0, min(100, current_scores.capacity + score_adjustments['capacity'])),
                    capital=max(0, min(100, current_scores.capital + score_adjustments['capital'])),
                    collateral=max(0, min(100, current_scores.collateral + score_adjustments['collateral'])),
                    conditions=max(0, min(100, current_scores.conditions + score_adjustments['conditions']))
                )
            
            result = {
                'detected_keywords': detected_keywords,
                'score_adjustments': score_adjustments,
                'total_adjustment': total_adjustment,
                'original_text': observations,
                'processed_text': processed_text,
                'classification_confidence': classification_results['scores'],
                'adjusted_scores': adjusted_scores
            }
            
            logger.info(f"Classified observations: {len(detected_keywords)} keywords, total adjustment: {total_adjustment}")
            return result
            
        except Exception as e:
            logger.error(f"Observation classification failed: {e}")
            return {
                'detected_keywords': [],
                'score_adjustments': {c: 0 for c in ['character', 'capacity', 'capital', 'collateral', 'conditions']},
                'total_adjustment': 0,
                'original_text': observations,
                'error': str(e)
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better classification"""
        if not text:
            return ""
        
        # Basic preprocessing
        processed = text.lower().strip()
        
        # Remove extra whitespace
        processed = ' '.join(processed.split())
        
        # Expand common abbreviations
        abbreviations = {
            'mach': 'machinery',
            'equip': 'equipment',
            'premises': 'premises',
            'util': 'utilised',
            'cap': 'capacity'
        }
        
        for abbrev, full in abbreviations.items():
            processed = processed.replace(f' {abbrev} ', f' {full} ')
            processed = processed.replace(f'{abbrev}.', f'{full}.')
        
        return processed
    
    async def batch_classify(
        self,
        observations_list: List[str],
        current_scores_list: Optional[List[FiveCScores]] = None
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple observations in batch
        
        Args:
            observations_list: List of observation texts
            current_scores_list: List of corresponding Five Cs scores
            
        Returns:
            List of classification results
        """
        try:
            if not self.classifier:
                await self.initialize()
            
            results = []
            
            # Process in batches to manage memory
            batch_size = 5
            for i in range(0, len(observations_list), batch_size):
                batch_texts = observations_list[i:i+batch_size]
                batch_scores = current_scores_list[i:i+batch_size] if current_scores_list else [None] * len(batch_texts)
                
                # Process batch
                batch_results = []
                for j, (text, scores) in enumerate(zip(batch_texts, batch_scores)):
                    result = await self.classify_observations(text, scores)
                    result['batch_index'] = i + j
                    batch_results.append(result)
                
                results.extend(batch_results)
                
                # Small delay to prevent overwhelming the model
                await asyncio.sleep(0.1)
            
            logger.info(f"Batch classified {len(observations_list)} observations")
            return results
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            return []
    
    def get_keyword_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get definitions and impact descriptions for all keywords"""
        return {
            keyword: {
                'description': self._get_keyword_description(keyword),
                'risk_level': self._get_keyword_risk_level(keyword),
                'score_impact': self.score_adjustments.get(keyword, {}),
                'examples': self.risk_keywords.get(keyword, [])
            }
            for keyword in self.risk_keywords.keys()
        }
    
    def _get_keyword_description(self, keyword: str) -> str:
        """Get description for a specific keyword"""
        descriptions = {
            'idle_machinery': 'Machinery or equipment that is not being used to its full capacity',
            'capacity_underutilised': 'Production facilities operating below optimal capacity levels',
            'promoter_absent': 'Key management personnel not actively involved in business operations',
            'overdue_creditors': 'Outstanding payments to suppliers or creditors',
            'working_capital_stress': 'Insufficient working capital to meet operational needs',
            'strong_management': 'Competent and experienced management team with good track record',
            'modern_facility': 'Well-maintained, modern equipment and infrastructure',
            'clean_premises': 'Clean, organized, and well-maintained business premises'
        }
        return descriptions.get(keyword, 'Unknown keyword')
    
    def _get_keyword_risk_level(self, keyword: str) -> str:
        """Get risk level for a specific keyword"""
        risk_levels = {
            'idle_machinery': 'HIGH',
            'capacity_underutilised': 'MEDIUM',
            'promoter_absent': 'CRITICAL',
            'overdue_creditors': 'HIGH',
            'working_capital_stress': 'HIGH',
            'strong_management': 'POSITIVE',
            'modern_facility': 'POSITIVE',
            'clean_premises': 'POSITIVE'
        }
        return risk_levels.get(keyword, 'MEDIUM')
    
    async def explain_classification(
        self,
        observations: str,
        detected_keywords: List[str]
    ) -> str:
        """
        Generate explanation for why certain keywords were detected
        
        Args:
            observations: Original observation text
            detected_keywords: List of detected keywords
            
        Returns:
            Explanation string
        """
        try:
            if not detected_keywords:
                return "No specific risk factors were identified in the observations."
            
            # Create explanation prompt
            prompt = f"""Explain why the following keywords were detected in the officer's observations:

Observations: {observations}

Detected Keywords: {', '.join(detected_keywords)}

For each detected keyword, explain:
1. What specific phrases or patterns triggered the detection
2. Why this is relevant for credit assessment
3. The potential impact on the borrower's credit profile

Provide a concise explanation that would help a credit officer understand the automated analysis."""

            # Get explanation from Ollama
            explanation = await ollama_client.generate(
                prompt=prompt,
                system="You are a credit analysis assistant explaining NLP classification results."
            )
            
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate classification explanation: {e}")
            return "Unable to generate explanation due to processing error."
    
    def cleanup(self):
        """Clean up resources"""
        if self.classifier:
            # Clear CUDA cache if applicable
            if hasattr(torch.cuda, 'empty_cache'):
                torch.cuda.empty_cache()
            
            self.classifier = None
            logger.info("NLP classifier resources cleaned up")

# Global instance
officer_portal_nlp = OfficerPortalNLP()
