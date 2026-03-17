import logging
import asyncio
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

from shared.models import ExtractedData, ValidationFlag, FiveCScores, CreditDecision
from config import config

logger = logging.getLogger(__name__)

class SHAPExplainer:
    """SHAP-based model explainability for Five Cs credit scoring"""
    
    def __init__(self):
        self.feature_names = [
            'revenue_inr', 'ebitda_inr', 'pat_inr', 'net_worth_inr',
            'total_debt_inr', 'fixed_assets_inr', 'cash_balance_inr',
            'gst_turnover_inr', 'itr_income_inr', 'cibil_cmr_rank',
            'cibil_overdue_inr', 'cibil_enquiries_6m', 'validation_flags_count',
            'sector_risk_score', 'promoter_experience_years', 'business_age_years'
        ]
        
        self.feature_descriptions = {
            'revenue_inr': 'Annual Revenue (INR)',
            'ebitda_inr': 'EBITDA (INR)',
            'pat_inr': 'Profit After Tax (INR)',
            'net_worth_inr': 'Net Worth (INR)',
            'total_debt_inr': 'Total Debt (INR)',
            'fixed_assets_inr': 'Fixed Assets (INR)',
            'cash_balance_inr': 'Cash Balance (INR)',
            'gst_turnover_inr': 'GST Turnover (INR)',
            'itr_income_inr': 'ITR Declared Income (INR)',
            'cibil_cmr_rank': 'CIBIL CMR Rank (1-10)',
            'cibil_overdue_inr': 'CIBIL Overdue Amount (INR)',
            'cibil_enquiries_6m': 'CIBIL Credit Enquiries (6 months)',
            'validation_flags_count': 'Number of Validation Flags',
            'sector_risk_score': 'Sector Risk Assessment Score',
            'promoter_experience_years': 'Promoter Experience (Years)',
            'business_age_years': 'Business Age (Years)'
        }
    
    async def generate_explanation(
        self,
        credit_decision: CreditDecision,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag]
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for credit scoring decision
        
        Args:
            credit_decision: Final credit decision with scores
            extracted_data: All extracted document data
            validation_flags: Cross-validation flags
            
        Returns:
            Dictionary with SHAP explanations and charts
        """
        try:
            logger.info("Generating SHAP explanation for credit decision")
            
            # Prepare feature data
            feature_data = self._prepare_feature_data(extracted_data, validation_flags, credit_decision)
            
            # Calculate SHAP values using mock model
            shap_values = self._calculate_mock_shap_values(feature_data, credit_decision.five_c_scores)
            
            # Generate visualizations
            summary_chart = await self._create_summary_plot(shap_values, feature_data)
            waterfall_chart = await self._create_waterfall_plot(shap_values, feature_data)
            feature_importance = await self._create_feature_importance_plot(shap_values, feature_data)
            
            # Generate explanations
            explanations = self._generate_explanations(shap_values, feature_data, credit_decision)
            
            result = {
                'explanation_type': 'SHAP',
                'model_type': 'Five_Cs_Credit_Scoring',
                'feature_data': feature_data,
                'shap_values': shap_values,
                'explanations': explanations,
                'charts': {
                    'summary_plot': summary_chart,
                    'waterfall_plot': waterfall_chart,
                    'feature_importance_plot': feature_importance
                },
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info("SHAP explanation generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"SHAP explanation generation failed: {e}")
            return {
                'explanation_type': 'SHAP',
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def _prepare_feature_data(
        self,
        extracted_data: List[ExtractedData],
        validation_flags: List[ValidationFlag],
        credit_decision: CreditDecision
    ) -> Dict[str, float]:
        """Prepare feature data for SHAP analysis"""
        try:
            # Initialize feature dictionary
            features = {name: 0.0 for name in self.feature_names}
            
            # Extract financial data
            financial_data = self._get_financial_data(extracted_data)
            if financial_data:
                features['revenue_inr'] = float(financial_data.revenue_inr or 0)
                features['ebitda_inr'] = float(financial_data.ebitda_inr or 0)
                features['pat_inr'] = float(financial_data.pat_inr or 0)
                features['net_worth_inr'] = float(financial_data.net_worth_inr or 0)
                features['total_debt_inr'] = float(financial_data.total_debt_inr or 0)
                features['fixed_assets_inr'] = float(financial_data.fixed_assets_inr or 0)
                features['cash_balance_inr'] = float(financial_data.cash_balance_inr or 0)
            
            # Extract GST data
            gst_data = self._get_gst_data(extracted_data)
            if gst_data:
                features['gst_turnover_inr'] = float(gst_data.gstr3b_turnover_inr or 0)
            
            # Extract ITR data
            itr_data = self._get_itr_data(extracted_data)
            if itr_data:
                features['itr_income_inr'] = float(itr_data.income_inr or 0)
            
            # Add CIBIL data
            if credit_decision.cibil_data:
                features['cibil_cmr_rank'] = float(credit_decision.cibil_data.cmr_rank or 7)
                features['cibil_overdue_inr'] = float(credit_decision.cibil_data.overdue_amount_inr or 0)
                features['cibil_enquiries_6m'] = float(credit_decision.cibil_data.credit_enquiries_6m or 0)
            
            # Add validation flags count
            features['validation_flags_count'] = float(len(validation_flags))
            
            # Add mock sector and promoter data
            features['sector_risk_score'] = np.random.uniform(0.3, 0.8)  # Mock sector risk
            features['promoter_experience_years'] = np.random.uniform(5, 25)  # Mock experience
            features['business_age_years'] = np.random.uniform(3, 15)  # Mock business age
            
            # Normalize features
            features = self._normalize_features(features)
            
            return features
            
        except Exception as e:
            logger.error(f"Feature data preparation failed: {e}")
            return {name: 0.0 for name in self.feature_names}
    
    def _calculate_mock_shap_values(
        self,
        feature_data: Dict[str, float],
        five_c_scores: FiveCScores
    ) -> Dict[str, float]:
        """Calculate mock SHAP values based on feature importance"""
        try:
            # Create mock SHAP values that explain the Five Cs scores
            shap_values = {}
            
            # Character score influenced by CIBIL, validation flags, promoter experience
            shap_values['character'] = (
                -0.3 * feature_data.get('cibil_cmr_rank', 7) / 10 +
                0.2 * feature_data.get('validation_flags_count', 0) +
                0.1 * feature_data.get('promoter_experience_years', 10) / 25 +
                np.random.normal(0, 0.1)
            )
            
            # Capacity score influenced by financial metrics
            shap_values['capacity'] = (
                0.4 * feature_data.get('ebitda_inr', 0) / 10000000 +
                -0.3 * feature_data.get('total_debt_inr', 0) / 10000000 +
                0.2 * feature_data.get('cash_balance_inr', 0) / 1000000 +
                np.random.normal(0, 0.1)
            )
            
            # Capital score influenced by net worth and assets
            shap_values['capital'] = (
                0.5 * feature_data.get('net_worth_inr', 0) / 10000000 +
                0.3 * feature_data.get('fixed_assets_inr', 0) / 10000000 +
                -0.2 * feature_data.get('business_age_years', 10) / 20 +
                np.random.normal(0, 0.1)
            )
            
            # Collateral score influenced by assets and sector risk
            shap_values['collateral'] = (
                0.6 * feature_data.get('fixed_assets_inr', 0) / 10000000 +
                -0.3 * feature_data.get('sector_risk_score', 0.5) +
                0.1 * feature_data.get('validation_flags_count', 0) +
                np.random.normal(0, 0.1)
            )
            
            # Conditions score influenced by sector and external factors
            shap_values['conditions'] = (
                -0.4 * feature_data.get('sector_risk_score', 0.5) +
                0.2 * feature_data.get('cibil_enquiries_6m', 0) / 10 +
                0.1 * feature_data.get('business_age_years', 10) / 20 +
                np.random.normal(0, 0.1)
            )
            
            return shap_values
            
        except Exception as e:
            logger.error(f"SHAP value calculation failed: {e}")
            return {c: 0.0 for c in ['character', 'capacity', 'capital', 'collateral', 'conditions']}
    
    def _normalize_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Normalize features to 0-1 range"""
        try:
            normalized = {}
            
            # Define normalization ranges
            ranges = {
                'revenue_inr': (0, 100000000),  # 0 to 10 Cr
                'ebitda_inr': (0, 20000000),    # 0 to 2 Cr
                'pat_inr': (0, 10000000),      # 0 to 1 Cr
                'net_worth_inr': (0, 50000000),   # 0 to 5 Cr
                'total_debt_inr': (0, 100000000),  # 0 to 10 Cr
                'fixed_assets_inr': (0, 200000000),  # 0 to 20 Cr
                'cash_balance_inr': (0, 10000000),   # 0 to 1 Cr
                'gst_turnover_inr': (0, 100000000), # 0 to 10 Cr
                'itr_income_inr': (0, 100000000),   # 0 to 10 Cr
                'cibil_cmr_rank': (1, 10),        # 1 to 10
                'cibil_overdue_inr': (0, 10000000), # 0 to 1 Cr
                'cibil_enquiries_6m': (0, 20),      # 0 to 20
                'validation_flags_count': (0, 10),    # 0 to 10
                'sector_risk_score': (0, 1),        # 0 to 1
                'promoter_experience_years': (0, 30), # 0 to 30
                'business_age_years': (0, 25)        # 0 to 25
            }
            
            for feature, value in features.items():
                if feature in ranges:
                    min_val, max_val = ranges[feature]
                    if max_val > min_val:
                        normalized[feature] = (value - min_val) / (max_val - min_val)
                    else:
                        normalized[feature] = 0.0
                else:
                    normalized[feature] = 0.0
            
            return normalized
            
        except Exception as e:
            logger.error(f"Feature normalization failed: {e}")
            return features
    
    async def _create_summary_plot(
        self,
        shap_values: Dict[str, float],
        feature_data: Dict[str, float]
    ) -> str:
        """Create summary SHAP plot"""
        try:
            # Create bar plot of SHAP values
            fig, ax = plt.subplots(figsize=(10, 6))
            
            scores = [shap_values[c] for c in ['character', 'capacity', 'capital', 'collateral', 'conditions']]
            score_names = ['Character', 'Capacity', 'Capital', 'Collateral', 'Conditions']
            colors = ['#e74c3c', '#3498db', '#f39c12', '#27ae60', '#8e44ad']
            
            bars = ax.bar(score_names, scores, color=colors)
            ax.set_title('Five Cs Score Contribution Analysis', fontsize=14, fontweight='bold')
            ax.set_ylabel('SHAP Value (Impact on Score)', fontsize=12)
            ax.set_xlabel('Credit Assessment Component', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars, scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                        f'{value:.2f}', ha='center', va='bottom', fontsize=10)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Summary plot creation failed: {e}")
            return ""
    
    async def _create_waterfall_plot(
        self,
        shap_values: Dict[str, float],
        feature_data: Dict[str, float]
    ) -> str:
        """Create waterfall plot showing feature contributions"""
        try:
            # Calculate base value and cumulative contributions
            base_value = 50.0  # Base score
            contributions = []
            cumulative = base_value
            
            # Prepare data for waterfall
            feature_contributions = [
                ('Base Value', base_value, 0),
                ('CIBIL Data', shap_values['character'] * 10, 0),
                ('Financial Metrics', shap_values['capacity'] * 10, 0),
                ('Net Worth', shap_values['capital'] * 10, 0),
                ('Assets', shap_values['collateral'] * 10, 0),
                ('Sector Risk', shap_values['conditions'] * 10, 0)
            ]
            
            # Calculate cumulative values
            for name, contribution, _ in feature_contributions[1:]:
                cumulative += contribution
                contributions.append((name, contribution, cumulative))
            
            # Create waterfall plot
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot bars
            y_positions = range(len(contributions))
            bar_colors = ['#95a5a6', '#3498db', '#f39c12', '#27ae60', '#8e44ad', '#e74c3c']
            
            for i, (name, contribution, _) in enumerate(contributions):
                if i == 0:
                    # Base value bar
                    ax.barh(i, contribution, color=bar_colors[i], alpha=0.7)
                else:
                    # Contribution bar
                    prev_cumulative = contributions[i-1][2] if i > 0 else base_value
                    ax.barh(i, contribution, left=prev_cumulative, color=bar_colors[i], alpha=0.7)
            
            # Add connecting lines
            for i in range(1, len(contributions)):
                prev_x = contributions[i-1][2]
                curr_x = contributions[i][2]
                ax.plot([prev_x, curr_x], [i-0.4, i-0.4], 'k-', alpha=0.5)
                ax.plot([prev_x, curr_x], [i+0.4, i+0.4], 'k-', alpha=0.5)
            
            # Customize plot
            ax.set_yticks(range(len(contributions)))
            ax.set_yticklabels([name for name, _, _ in contributions])
            ax.set_xlabel('Credit Score', fontsize=12)
            ax.set_title('Five Cs Score Breakdown (Waterfall)', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='x')
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Waterfall plot creation failed: {e}")
            return ""
    
    async def _create_feature_importance_plot(
        self,
        shap_values: Dict[str, float],
        feature_data: Dict[str, float]
    ) -> str:
        """Create feature importance plot"""
        try:
            # Calculate absolute feature importance
            feature_importance = {
                'Revenue': abs(feature_data.get('revenue_inr', 0)),
                'EBITDA': abs(feature_data.get('ebitda_inr', 0)),
                'Net Worth': abs(feature_data.get('net_worth_inr', 0)),
                'Total Debt': abs(feature_data.get('total_debt_inr', 0)),
                'Fixed Assets': abs(feature_data.get('fixed_assets_inr', 0)),
                'GST Turnover': abs(feature_data.get('gst_turnover_inr', 0)),
                'CIBIL Rank': abs(feature_data.get('cibil_cmr_rank', 7)),
                'Validation Flags': abs(feature_data.get('validation_flags_count', 0))
            }
            
            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # Create horizontal bar plot
            fig, ax = plt.subplots(figsize=(10, 8))
            
            features = [f[0] for f in sorted_features]
            importance = [f[1] for f in sorted_features]
            
            bars = ax.barh(features, importance, color='skyblue')
            ax.set_title('Feature Importance for Credit Decision', fontsize=14, fontweight='bold')
            ax.set_xlabel('Importance Score', fontsize=12)
            ax.set_ylabel('Features', fontsize=12)
            
            # Add value labels
            for bar, value in zip(bars, importance):
                width = bar.get_width()
                ax.text(width + 0.01, bar.get_y() + bar.get_height()/2.,
                        f'{value:.0f}', ha='left', va='center', fontsize=10)
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Feature importance plot creation failed: {e}")
            return ""
    
    def _generate_explanations(
        self,
        shap_values: Dict[str, float],
        feature_data: Dict[str, float],
        credit_decision: CreditDecision
    ) -> List[Dict[str, Any]]:
        """Generate human-readable explanations for SHAP values"""
        try:
            explanations = []
            
            for c_name, c_value in credit_decision.five_c_scores.__dict__.items():
                shap_value = shap_values.get(c_name.lower(), 0)
                
                explanation = {
                    'component': c_name.title(),
                    'score': c_value,
                    'shap_value': shap_value,
                    'impact': 'positive' if shap_value > 0 else 'negative',
                    'explanation': self._get_explanation_text(c_name.lower(), shap_value, feature_data)
                }
                explanations.append(explanation)
            
            return explanations
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return []
    
    def _get_explanation_text(
        self,
        component: str,
        shap_value: float,
        feature_data: Dict[str, float]
    ) -> str:
        """Get explanation text for a specific component"""
        explanations = {
            'character': f"CIBIL rank ({feature_data.get('cibil_cmr_rank', 7):.0f}) and validation flags ({feature_data.get('validation_flags_count', 0)}) {'increased' if shap_value > 0 else 'decreased'} the character score by {abs(shap_value):.1f} points.",
            'capacity': f"Financial metrics including EBITDA ({feature_data.get('ebitda_inr', 0):,.0f}) and debt levels {'improved' if shap_value > 0 else 'reduced'} capacity assessment by {abs(shap_value):.1f} points.",
            'capital': f"Net worth ({feature_data.get('net_worth_inr', 0):,.0f}) and fixed assets ({feature_data.get('fixed_assets_inr', 0):,.0f}) {'strengthened' if shap_value > 0 else 'weakened'} capital position by {abs(shap_value):.1f} points.",
            'collateral': f"Asset base ({feature_data.get('fixed_assets_inr', 0):,.0f}) and sector risk ({feature_data.get('sector_risk_score', 0.5):.2f}) {'enhanced' if shap_value > 0 else 'reduced'} collateral assessment by {abs(shap_value):.1f} points.",
            'conditions': f"Sector conditions ({feature_data.get('sector_risk_score', 0.5):.2f}) and external factors {'improved' if shap_value > 0 else 'worsened'} conditions assessment by {abs(shap_value):.1f} points."
        }
        
        return explanations.get(component, "Component analysis completed.")
    
    def _get_financial_data(self, extracted_data: List[ExtractedData]):
        """Extract financial data from extracted documents"""
        for data in extracted_data:
            if data.document_type.value == 'financial_statement' and data.financial_fields:
                return data.financial_fields
        return None
    
    def _get_gst_data(self, extracted_data: List[ExtractedData]):
        """Extract GST data from extracted documents"""
        for data in extracted_data:
            if data.document_type.value == 'gst_return' and data.gst_fields:
                return data.gst_fields
        return None
    
    def _get_itr_data(self, extracted_data: List[ExtractedData]):
        """Extract ITR data from extracted documents"""
        for data in extracted_data:
            if data.document_type.value == 'itr' and data.itr_fields:
                return data.itr_fields
        return None

# Global instance
shap_explainer = SHAPExplainer()
