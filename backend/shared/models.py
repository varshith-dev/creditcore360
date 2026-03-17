from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    FINANCIAL_STATEMENT = "financial_statement"
    BANK_STATEMENT = "bank_statement"
    GST_RETURN = "gst_return"
    ITR = "itr"
    LEGAL_COLLATERAL = "legal_collateral"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PageResult(BaseModel):
    text: str
    confidence: float
    language: str

class ExtractedDocument(BaseModel):
    pages: List[PageResult]
    low_confidence_pages: List[int]
    total_pages: int

class FinancialFields(BaseModel):
    revenue_inr: Optional[float] = None
    ebitda_inr: Optional[float] = None
    pat_inr: Optional[float] = None
    net_worth_inr: Optional[float] = None
    total_debt_inr: Optional[float] = None
    fixed_assets_inr: Optional[float] = None
    financial_year: Optional[str] = None

class BankStatementFields(BaseModel):
    avg_monthly_balance_inr: Optional[float] = None
    total_credits_inr: Optional[float] = None
    total_debits_inr: Optional[float] = None
    large_cash_withdrawals_inr: Optional[float] = None
    bounce_count: Optional[int] = None
    emi_obligations_inr: Optional[float] = None

class GSTFields(BaseModel):
    gstr3b_annual_turnover_inr: Optional[float] = None
    gstr2a_itc_claimed_inr: Optional[float] = None
    gstr3b_tax_paid_inr: Optional[float] = None

class ITRFields(BaseModel):
    itr_declared_income_inr: Optional[float] = None
    itr_year: Optional[str] = None
    source_of_income: Optional[str] = None

class LegalCollateralFields(BaseModel):
    collateral_description: Optional[str] = None
    collateral_value_inr: Optional[float] = None
    promoter_guarantee_clauses: Optional[List[str]] = None
    contingent_liabilities_inr: Optional[float] = None

class ValidationFlag(BaseModel):
    flag_type: str
    severity: Severity
    description: str
    affected_fields: List[str]
    raw_values: Dict[str, Any]

class ExtractedData(BaseModel):
    document_type: DocumentType
    financial_fields: Optional[FinancialFields] = None
    bank_fields: Optional[BankStatementFields] = None
    gst_fields: Optional[GSTFields] = None
    itr_fields: Optional[ITRFields] = None
    legal_fields: Optional[LegalCollateralFields] = None
    validation_flags: List[ValidationFlag] = []
    extraction_confidence: float
    processed_at: datetime = Field(default_factory=datetime.now)

class CourtCase(BaseModel):
    case_number: str
    case_type: str
    filing_date: Optional[datetime] = None
    current_status: str
    court_name: str

class DirectorProfile(BaseModel):
    din: str
    name: str
    active_directorships: int
    resigned_directorships: int
    struck_off_companies: int
    compliance_score: float

class ChargeRegistry(BaseModel):
    total_charges: int
    open_charges: int
    satisfied_charges: int
    latest_charge_date: Optional[datetime] = None

class RiskFinding(BaseModel):
    category: str
    severity: Severity
    description: str
    source: str
    raw_data: Dict[str, Any]
    detected_at: datetime = Field(default_factory=datetime.now)

class ResearchReport(BaseModel):
    company_name: str
    cin: str
    findings: List[RiskFinding]
    court_cases: List[CourtCase] = []
    director_profiles: List[DirectorProfile] = []
    charge_registry: Optional[ChargeRegistry] = None
    news_sentiment: Optional[str] = None
    rbi_alerts: List[str] = []
    research_completed_at: datetime = Field(default_factory=datetime.now)

class FiveCScores(BaseModel):
    character: float = Field(ge=0, le=100)
    capacity: float = Field(ge=0, le=100)
    capital: float = Field(ge=0, le=100)
    collateral: float = Field(ge=0, le=100)
    conditions: float = Field(ge=0, le=100)
    
    def get_weighted_score(self) -> float:
        weights = {
            'character': 0.25,
            'capacity': 0.30,
            'capital': 0.20,
            'collateral': 0.15,
            'conditions': 0.10
        }
        return sum(
            getattr(self, key) * weight 
            for key, weight in weights.items()
        )

class CreditGrade(str, Enum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    DECLINE = "DECLINE"

class DPDEntry(BaseModel):
    month: str
    days_past_due: int

class CIBILData(BaseModel):
    cmr_rank: int = Field(ge=1, le=10)
    overdue_amount_inr: float = Field(ge=0)
    active_credit_facilities: List[str] = []
    dpd_history_36m: List[DPDEntry] = []
    credit_enquiries_6m: int = Field(ge=0)

class LoanLimitResult(BaseModel):
    final_limit_inr: float
    cash_flow_ceiling_inr: float
    asset_ceiling_inr: float
    sector_ceiling_inr: float
    binding_ceiling: str

class CreditDecision(BaseModel):
    company_name: str
    cin: str
    five_c_scores: FiveCScores
    total_score: float
    grade: CreditGrade
    cibil_data: Optional[CIBILData] = None
    loan_limit: Optional[LoanLimitResult] = None
    interest_rate_pct: Optional[float] = None
    tenor_months: Optional[int] = None
    decision_at: datetime = Field(default_factory=datetime.now)

class CAMDocument(BaseModel):
    word_path: str
    pdf_path: str
    decision: CreditDecision
    research_report: Optional[ResearchReport] = None
    extracted_data: List[ExtractedData] = []
    officer_observations: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobStage(str, Enum):
    OCR_EXTRACTION = "ocr_extraction"
    CROSS_VALIDATION = "cross_validation"
    RESEARCH_AGENT = "research_agent"
    OFFICER_SCORING = "officer_scoring"
    FIVE_CS_SCORING = "five_cs_scoring"
    CAM_GENERATION = "cam_generation"

class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    stage: Optional[JobStage] = None
    progress_pct: float = Field(ge=0, le=100)
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
