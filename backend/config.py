import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Ollama Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss")
    OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    
    # AWS Textract Configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    
    # External API Keys
    ECOURTS_API_KEY = os.getenv("ECOURTS_API_KEY")
    MCA21_API_KEY = os.getenv("MCA21_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    CIBIL_B2B_CLIENT_ID = os.getenv("CIBIL_B2B_CLIENT_ID")
    CIBIL_B2B_CLIENT_SECRET = os.getenv("CIBIL_B2B_CLIENT_SECRET")
    
    # Vivriti Sector Exposure Caps (INR Crores)
    SECTOR_CAPS = {
        "NBFC": float(os.getenv("SECTOR_CAP_NBFC", "500")),
        "MANUFACTURING": float(os.getenv("SECTOR_CAP_MANUFACTURING", "200")),
        "TRADING": float(os.getenv("SECTOR_CAP_TRADING", "100")),
        "SERVICES": float(os.getenv("SECTOR_CAP_SERVICES", "150"))
    }
    
    # Application Settings
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "70"))
    CAM_OUTPUT_DIR = os.getenv("CAM_OUTPUT_DIR", "/tmp/cam_outputs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # OCR Settings
    TESSERACT_LANGUAGES = os.getenv("TESSERACT_LANGUAGES", "hin+eng")
    
    # ML Model Settings
    DISTILBERT_MODEL = os.getenv("DISTILBERT_MODEL", "facebook/bart-large-mnli")
    SHAP_MODEL_TYPE = os.getenv("SHAP_MODEL_TYPE", "linear")
    
    # Business Logic Constants
    DSCR_COMFORT_FACTOR = float(os.getenv("DSCR_COMFORT_FACTOR", "0.85"))
    LOAN_MULTIPLIER = float(os.getenv("LOAN_MULTIPLIER", "4"))
    ASSET_LEVERAGE_RATIO = float(os.getenv("ASSET_LEVERAGE_RATIO", "0.60"))
    
    # Validation Thresholds
    GST_ITC_MISMATCH_THRESHOLD = float(os.getenv("GST_ITC_MISMATCH_THRESHOLD", "0.15"))
    REVENUE_INFLATION_THRESHOLD = float(os.getenv("REVENUE_INFLATION_THRESHOLD", "0.25"))
    HEADCOUNT_VARIANCE_THRESHOLD = float(os.getenv("HEADCOUNT_VARIANCE_THRESHOLD", "0.40"))
    CASH_LEAKAGE_THRESHOLD = float(os.getenv("CASH_LEAKAGE_THRESHOLD", "0.30"))
    
    # Score Adjustment Rules
    SCORE_ADJUSTMENTS = {
        "idle_machinery": {"capacity": -8},
        "capacity_underutilised": {"capacity": -5},
        "promoter_absent": {"character": -10},
        "overdue_creditors": {"capital": -7},
        "working_capital_stress": {"capacity": -6},
        "strong_management": {"character": 5},
        "modern_facility": {"collateral": 3},
        "clean_premises": {"character": 3}
    }
    
    # Risk Classification Thresholds
    RISK_THRESHOLDS = {
        "LOW_RISK_MIN": 85,
        "MODERATE_RISK_MIN": 70,
        "HIGH_RISK_MIN": 50
    }
    
    # CIBIL Risk Rules
    CIBIL_RISK_RULES = {
        "CMR_RANK_THRESHOLD": 5,
        "MAX_ENQUIRIES_6M": 6,
        "MAX_DPD_DAYS": 30
    }
    
    # API Timeouts (seconds)
    API_TIMEOUTS = {
        "ECOURTS": 30,
        "MCA21": 30,
        "NEWS_API": 30,
        "CIBIL": 45,
        "RBI_FEED": 30
    }
    
    @classmethod
    def get_sector_cap(cls, sector: str) -> float:
        """Get sector exposure cap in INR Crores"""
        return cls.SECTOR_CAPS.get(sector.upper(), 100.0)  # Default 100 Cr
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate required configuration"""
        required_vars = [
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required environment variables: {missing_vars}")
            return False
        
        return True

config = Config()
