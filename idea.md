# Intelli-Credit — AI-Powered Corporate Credit Appraisal Engine
## Windsurf Agent Build Prompt (Full Stack)

---

## ROLE & CONTEXT

You are a senior full-stack engineer building **Intelli-Credit**, an end-to-end AI-powered Credit Decisioning Engine for India's mid-market lending landscape. The system runs entirely on a **self-hosted Azure VM** (Standard_B4as_v2: 4 vCPU, 16 GB RAM, 128 GB SSD, Ubuntu 24.04). All AI inference runs **locally via Ollama** — no external AI API calls, no per-token billing, no borrower data leaving the server.

Public domain: `system.truvgo.tech`
VM IP: `4.213.160.42`
Local Ollama endpoint: `http://127.0.0.1:11434`
Primary model: `gpt-oss` (≈13 GB, already pulled)

The application is accessed via a **Webtop browser-based Linux desktop** (XFCE, port 3000). Credit officers open the browser inside that desktop and use the entire system — uploading documents, running analysis, reading results, downloading the final CAM — without installing anything locally.

---

## TECH STACK

- **Runtime**: Python 3.11, FastAPI (backend), Jinja2 + Vanilla JS (frontend UI inside Webtop)
- **AI inference**: Ollama REST API (`http://127.0.0.1:11434/api/generate`)
- **OCR**: Tesseract 5 (`hin+eng`), OpenCV 4 for pre-processing
- **Document parsing**: pdfplumber (digital PDFs), openpyxl (Excel bank statements)
- **NLP classifier**: DistilBERT via HuggingFace Transformers (fine-tuned for risk keywords)
- **Graph analysis**: NetworkX (circular trading detection)
- **ML explainability**: SHAP
- **Report generation**: python-docx (Word), ReportLab (PDF)
- **Containerisation**: Docker + Docker Compose
- **Reverse proxy**: Nginx
- **TLS**: Let's Encrypt via Certbot
- **External APIs**: AWS Textract (OCR fallback), TransUnion CIBIL B2B, e-Courts, MCA21, NewsAPI.org, RBI RSS feed

---

## PROJECT STRUCTURE TO CREATE
```
intelli-credit/
├── docker-compose.yml
├── nginx/
│   └── default.conf
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entrypoint
│   ├── config.py                # All env vars and constants
│   ├── pillar1_ingestor/
│   │   ├── __init__.py
│   │   ├── document_router.py   # Accepts uploads, routes by file type
│   │   ├── ocr_pipeline.py      # OpenCV pre-process → Tesseract → confidence check
│   │   ├── textract_fallback.py # AWS Textract for low-confidence docs
│   │   ├── field_extractor.py   # Ollama prompt → structured JSON fields
│   │   └── cross_validator.py   # 5 cross-validation checks
│   ├── pillar2_research/
│   │   ├── __init__.py
│   │   ├── agent_loop.py        # Agentic plan → fetch → synthesise loop
│   │   ├── ecourts_client.py
│   │   ├── mca21_client.py
│   │   ├── news_client.py
│   │   ├── rbi_feed_client.py
│   │   ├── risk_synthesiser.py  # Ollama synthesis prompt
│   │   └── officer_portal.py   # DistilBERT NLP classifier + score adjustments
│   ├── pillar3_engine/
│   │   ├── __init__.py
│   │   ├── five_cs_scorer.py    # Weighted scoring model
│   │   ├── cibil_client.py      # TransUnion CIBIL B2B API
│   │   ├── loan_limit_calc.py   # 3-ceiling minimum logic
│   │   ├── shap_explainer.py    # SHAP feature importance
│   │   └── cam_generator.py     # Ollama → python-docx + ReportLab
│   └── shared/
│       ├── ollama_client.py     # Reusable Ollama API wrapper
│       ├── models.py            # Pydantic data models
│       └── exceptions.py
└── frontend/
    ├── templates/
    │   ├── base.html
    │   ├── upload.html          # Document upload UI
    │   ├── officer_portal.html  # Free-text observations input
    │   ├── results.html         # Five Cs scores + risk flags dashboard
    │   └── cam_preview.html     # CAM summary + download buttons
    └── static/
        ├── styles.css
        └── app.js
```

---

## STEP-BY-STEP BUILD INSTRUCTIONS

Work through each step fully before moving to the next. After each step, confirm the milestone runs without errors.

---

### STEP 1 — Docker Compose & Infrastructure

Create `docker-compose.yml` with these services:
- `webtop`: `lscr.io/linuxserver/webtop:ubuntu-xfce`, port 3000, volumes for persistent home
- `backend`: build from `./backend`, port 8000, `network_mode: host` so it can reach Ollama at 127.0.0.1:11434
- `nginx`: build from `./nginx`, ports 80 and 443

Create `nginx/default.conf`:
- Route `system.truvgo.tech` → `http://localhost:3000` (Webtop)
- Route `system.truvgo.tech/api` → `http://localhost:8000` (FastAPI backend)
- TLS termination with Let's Encrypt certs at `/etc/letsencrypt/live/system.truvgo.tech/`

Create `backend/requirements.txt` with all dependencies:
```
fastapi uvicorn[standard] python-multipart
pdfplumber openpyxl pillow
opencv-python-headless pytesseract
boto3                          # AWS Textract fallback
transformers torch             # DistilBERT NLP
networkx                       # Circular trading graph
shap scikit-learn numpy pandas
python-docx reportlab
httpx aiohttp                  # Async HTTP clients for external APIs
pydantic python-dotenv
```

**Milestone**: `docker compose up` starts all three services. `curl http://localhost:8000/health` returns `{"status": "ok"}`.

---

### STEP 2 — Shared Ollama Client (`shared/ollama_client.py`)

Create an async wrapper around the Ollama API:
```python
# Interface to implement:

async def generate(prompt: str, system: str = "", temperature: float = 0.1) -> str:
    """POST to http://127.0.0.1:11434/api/generate with model='gpt-oss'.
    Stream=False. Return the response string. Raise OllamaUnavailableError
    if the endpoint is unreachable."""

async def extract_json(prompt: str, system: str = "") -> dict:
    """Call generate(), then parse the response as JSON.
    Strip markdown fences (```json ... ```) before parsing.
    Retry once if JSON parsing fails."""
```

Add a `/health` check endpoint in `main.py` that also pings Ollama and reports its status.

**Milestone**: `curl http://localhost:8000/health` returns Ollama status as `reachable` or `unreachable`.

---

### STEP 3 — Pillar 1: Data Ingestor

#### 3a. OCR Pipeline (`ocr_pipeline.py`)
```python
# Input: file bytes + mime type
# Output: ExtractedDocument(pages: list[PageResult], low_confidence_pages: list[int])

# PageResult: text: str, confidence: float, language: str

# Pipeline:
# 1. If PDF: use pdfplumber to extract text. If text layer exists and len > 100 chars, skip OCR.
# 2. If scanned/image PDF: convert pages to PIL images using pdf2image.
# 3. OpenCV pre-processing per page image:
#    - Convert to grayscale
#    - Deskew: compute skew angle via Hough line transform, rotate to correct
#    - Binarise: adaptive threshold (cv2.THRESH_BINARY + cv2.ADAPTIVE_THRESH_GAUSSIAN_C)
#    - Denoise: cv2.fastNlMeansDenoising
# 4. Tesseract OCR with lang='hin+eng', output_type=Output.DICT
# 5. Compute per-page mean confidence from Tesseract's conf values
# 6. If confidence < 70, add page to low_confidence_pages list
#    (do NOT discard — flag it and continue)
# 7. If more than 30% of pages are low confidence, trigger Textract fallback
```

#### 3b. AWS Textract Fallback (`textract_fallback.py`)
```python
# Use boto3 Textract detect_document_text for single pages
# Use start_document_text_detection + get_document_text_detection for multi-page async
# Reassemble blocks by page into full text strings
# Handle rupee symbol (₹) which Textract supports natively
```

#### 3c. Field Extractor (`field_extractor.py`)

Build a structured extraction prompt system. For each document type, define a system prompt and extraction schema:

**Financial statements** — extract: `revenue_inr`, `ebitda_inr`, `pat_inr`, `net_worth_inr`, `total_debt_inr`, `fixed_assets_inr`, `financial_year`

**Bank statements** — extract: `avg_monthly_balance_inr`, `total_credits_inr`, `total_debits_inr`, `large_cash_withdrawals_inr`, `bounce_count`, `emi_obligations_inr`

**GST returns** — extract: `gstr3b_annual_turnover_inr`, `gstr2a_itc_claimed_inr`, `gstr3b_tax_paid_inr`

**ITR documents** — extract: `itr_declared_income_inr`, `itr_year`, `source_of_income`

**Legal/collateral** — extract: `collateral_description`, `collateral_value_inr`, `promoter_guarantee_clauses`, `contingent_liabilities_inr`

The Ollama prompt must instruct the model to:
- Return ONLY valid JSON matching the schema
- Use `null` for fields not found in the document
- Never hallucinate figures — only extract explicitly stated numbers
- Flag ambiguous figures with an `_uncertain: true` suffix field

#### 3d. Cross Validator (`cross_validator.py`)

Implement all 5 checks as async functions that run concurrently via `asyncio.gather()`:
```python
# Check 1: GSTR-2A vs GSTR-3B ITC delta
# Rule: abs(gstr2a_itc - gstr3b_itc) / gstr3b_itc > 0.15 → FLAG
# Flag type: "GST_ITC_MISMATCH", severity: "HIGH"

# Check 2: ITR income vs GST turnover
# Rule: abs(itr_income - gst_turnover) / gst_turnover > 0.25 → FLAG
# Flag type: "REVENUE_INFLATION_RISK", severity: "HIGH"

# Check 3: TDS filings vs headcount
# Rule: (tds_total_salary / avg_salary_assumption) vs declared_headcount
# If implied headcount differs by >40% → FLAG
# Flag type: "LABOUR_COST_MANIPULATION", severity: "MEDIUM"

# Check 4: Bank withdrawals vs declared opex
# Rule: cash_withdrawals > 0.30 * declared_opex → FLAG
# Flag type: "CASH_LEAKAGE_RISK", severity: "MEDIUM"

# Check 5: Circular trading detection (NetworkX)
# Build directed graph: nodes = GST numbers, edges = invoices
# For each connected component, check if any node has in-degree AND out-degree > 0
# with transaction within 30 days of original — flag as circular
# Flag type: "CIRCULAR_TRADING_DETECTED", severity: "CRITICAL"
```

Each flag: `{flag_type, severity, description, affected_fields, raw_values}`.

**Milestone**: POST a sample PDF to `/api/ingest` → returns structured JSON with extracted fields + validation flags within 3 minutes.

---

### STEP 4 — Pillar 2: Research Agent

#### 4a. Agent Loop (`agent_loop.py`)
```python
# Entry: run_research_agent(company_name: str, cin: str, promoter_pans: list[str]) -> ResearchReport

# Loop:
# 1. PLAN — send company context to Ollama, ask it to list which queries to run
#    and why (e-Courts by CIN, MCA21 by DIN list, news by name + sector)
# 2. FETCH — call all API clients concurrently (asyncio.gather)
# 3. SYNTHESISE — pass all raw API results to Ollama synthesis prompt
#    Prompt instructs model to: identify contradictions, produce one RiskFinding
#    per anomaly, assign severity (LOW/MEDIUM/HIGH/CRITICAL)
# 4. Return ResearchReport(findings: list[RiskFinding], raw_data: dict)
```

#### 4b. e-Courts Client (`ecourts_client.py`)
```python
# Query pending suits by CIN or promoter PAN
# Parse: case_number, case_type, filing_date, current_status, court_name
# Special rules:
#   - If case_type contains "WINDING UP" or "NCLT" → auto-flag CRITICAL
#   - If case_type contains "DRT" or "DEBT RECOVERY" → flag HIGH
# Return: list[CourtCase]
```

#### 4c. MCA21 Client (`mca21_client.py`)
```python
# DIN-based lookup for each promoter:
#   - All directorships (active + resigned)
#   - Count of struck-off companies in director history
#   - Charge registry status for the borrower company (open/satisfied charges)
#   - Annual filing compliance: check for missing filings in last 3 years
# Return: DirectorProfile per promoter, ChargeRegistry for the company
```

#### 4d. News + RBI Feed (`news_client.py`, `rbi_feed_client.py`)
```python
# NewsAPI: query by company_name + promoter names, last 90 days
# Google News RSS: same query, parse feed entries
# Filter out irrelevant results using Ollama relevance check
# RBI feed: poll https://www.rbi.org.in/rss/rss.aspx
# Filter for circulars affecting borrower's sector (passed as context)
```

#### 4e. Officer Portal Backend (`officer_portal.py`)
```python
# POST /api/officer-observations
# Input: free_text observation string, current_scores: dict (Five Cs scores)
# 
# DistilBERT NLP classifier:
#   Load fine-tuned checkpoint (or use zero-shot with 'facebook/bart-large-mnli')
#   Labels: ["idle_machinery", "capacity_underutilised", "promoter_absent",
#            "overdue_creditors", "strong_management", "modern_facility",
#            "working_capital_stress", "clean_premises"]
#
# Score deduction table (apply to relevant C):
#   idle_machinery        → Capacity  -8
#   capacity_underutilised → Capacity -5
#   promoter_absent       → Character -10
#   overdue_creditors     → Capital   -7
#   working_capital_stress → Capacity -6
#   strong_management     → Character +5
#   modern_facility       → Collateral +3
#   clean_premises        → Character +3
#
# Return: updated_scores, detected_keywords, adjustments_applied, original_text
# (original_text is stored verbatim — it prints in the CAM)
```

**Milestone**: POST `{"company": "Acme Industries", "cin": "U12345MH2010PLC123456"}` to `/api/research` → returns structured `ResearchReport` with findings from all four sources.

---

### STEP 5 — Pillar 3: Recommendation Engine & CAM Generator

#### 5a. Five Cs Scorer (`five_cs_scorer.py`)
```python
# Each C scored 0–100, then weighted:
# Character  25% — from MCA21 compliance score + e-Courts clean flag + promoter track record
# Capacity   30% — from DSCR: (EBITDA / total_debt_obligations); trend across 3 years
# Capital    20% — from net worth / total assets ratio + GSTR-3B payment consistency
# Collateral 15% — from ROC charge registry + collateral_value / loan_amount ratio
# Conditions 10% — from RBI sector risk flag + news sentiment score
#
# Total score = sum of weighted C scores
# Grade mapping:
#   85–100 → LOW RISK (Green)
#   70–84  → MODERATE RISK (Yellow)
#   50–69  → HIGH RISK (Orange)
#   < 50   → DECLINE (Red)
#
# Each C score must store: score, weight, contributing_factors[], data_sources[]
# These print in the CAM as traceable evidence
```

#### 5b. CIBIL Client (`cibil_client.py`)
```python
# TransUnion CIBIL B2B API
# Input: company_cin OR company_pan
# Extract:
#   cmr_rank: int (1–10)
#   overdue_amount_inr: float
#   active_credit_facilities: list
#   dpd_history_36m: list[DPDEntry]   # each: month, days_past_due
#   credit_enquiries_6m: int
#
# Business rules:
#   cmr_rank < 5  → HIGH_RISK flag in CAM header (bold red)
#   overdue_amount > 0 → flag with amount
#   dpd_history any entry > 30 → flag
#   credit_enquiries_6m > 6 → flag (credit hunger signal)
```

#### 5c. Loan Limit Calculator (`loan_limit_calc.py`)
```python
# Three independent ceilings — take the MINIMUM:
#
# Ceiling 1: Cash flow based
#   avg_3yr_free_cash_flow = mean of last 3 years (EBITDA - capex - taxes - interest)
#   DSCR_adjusted_fcf = avg_3yr_free_cash_flow * dscr_comfort_factor (default 0.85)
#   ceiling_1 = 4 * DSCR_adjusted_fcf
#
# Ceiling 2: Asset based
#   net_tangible_assets = fixed_assets + net_current_assets - intangibles
#   ceiling_2 = 0.60 * net_tangible_assets
#
# Ceiling 3: Sector exposure cap
#   Lookup Vivriti's sector_exposure_caps dict by borrower sector
#   ceiling_3 = sector_cap_inr (configured in config.py)
#
# Final loan_limit = min(ceiling_1, ceiling_2, ceiling_3)
# Store which ceiling was binding — this prints in the CAM
```

#### 5d. SHAP Explainer (`shap_explainer.py`)
```python
# Build a feature vector from all scored inputs
# Use shap.Explainer on a simple scoring model (LinearRegression or GradientBoosting)
# Generate SHAP values for the final credit decision
# Produce a bar chart as a PNG (matplotlib, saved to /tmp/shap_chart.png)
# The chart shows top 10 features that drove the rate up or down
# Chart title: "What drove your interest rate"
```

#### 5e. CAM Generator (`cam_generator.py`)
```python
# Step 1: Build CAM data dict with all findings, scores, flags, officer observations
#
# Step 2: Generate narrative sections via Ollama
# Use one prompt per section to avoid context length issues:
#   - Executive Summary (3 items: decision, loan limit in ₹ Cr, interest rate + one sentence reason)
#   - Character section narrative
#   - Capacity section narrative
#   - Capital section narrative
#   - Collateral section narrative
#   - Conditions section narrative
#   - Risk Flags summary
#
# Ollama system prompt for each section:
#   "You are a senior credit analyst writing a formal Credit Appraisal Memo for
#    Vivriti Capital's credit committee. Write in formal Indian banking English.
#    Be specific — cite actual figures. Do not hedge excessively.
#    Maximum 200 words per section. Output plain text only, no markdown."
#
# Step 3: Assemble Word document (python-docx):
#   - Vivriti Capital header with date and borrower name
#   - Executive Summary box (3 lines, bold)
#   - For each C: section heading, narrative paragraph, data table, risk flags
#   - CIBIL summary table
#   - Loan structure: limit, tenor, interest rate, security
#   - SHAP chart image embedded in appendix
#   - Officer site visit observations (verbatim, italicised, labelled "Field Observations")
#   - Page numbers, footer with analyst name and date
#
# Step 4: Convert to PDF via ReportLab (render same structure)
#
# Step 5: Save both to /tmp/cam_{cin}_{timestamp}.docx and .pdf
# Return: {word_path, pdf_path, decision, loan_limit_inr, interest_rate_pct}
```

**Milestone**: Feed sample data into Pillar 3 → downloadable `.docx` and `.pdf` CAM files produced with all sections populated.

---

### STEP 6 — Frontend UI (Jinja2 + Vanilla JS)

Build four screens accessible from the Webtop browser at `http://localhost:8000`:

#### Screen 1 — Document Upload (`upload.html`)
- Drag-and-drop upload zone supporting PDF, XLSX, JSON (multiple files)
- Document type selector per file: Financial Statement / Bank Statement / GST Return / ITR / Legal Agreement
- Progress indicator showing OCR → extraction → validation stages
- On completion: redirect to Screen 2 (officer portal) with `session_id`

#### Screen 2 — Officer Observations (`officer_portal.html`)
- Large free-text area: "Enter your factory visit / management interview notes"
- Real-time keyword detection: as the officer types, detected risk keywords highlight inline
- Current Five Cs scores shown as adjustable sliders with manual override
- Mandatory reason field appears when a score is manually adjusted
- "Run Full Analysis" button → triggers Pillar 2 research agent + Pillar 3 engine

#### Screen 3 — Results Dashboard (`results.html`)
- Five Cs radar chart (Chart.js or SVG)
- Risk flags panel: CRITICAL (red), HIGH (orange), MEDIUM (yellow), LOW (grey)
- CIBIL CMR rank badge (colour-coded by risk)
- Research findings accordion (e-Courts, MCA21, News, RBI)
- Cross-validation flags with supporting data
- Loan structure summary: limit, tenor, rate

#### Screen 4 — CAM Preview + Download (`cam_preview.html`)
- Executive Summary card: Decision badge (APPROVE / DECLINE / REFER), Loan Limit, Interest Rate
- Download buttons: "Download Word (.docx)" and "Download PDF (.pdf)"
- SHAP chart displayed inline
- Officer observations shown verbatim in a callout box

**Milestone**: Full end-to-end flow works in a browser — upload documents, enter observations, click analyse, view results, download CAM.

---

### STEP 7 — End-to-End Integration & Async Job Queue

The full pipeline (OCR → extraction → research → scoring → CAM) takes 15–30 minutes. Implement as a background job:
```python
# POST /api/jobs/start → returns {job_id}
# GET  /api/jobs/{job_id}/status → returns {stage, progress_pct, status, error}
# GET  /api/jobs/{job_id}/result → returns full result once complete

# Stages:
# 1. ocr_extraction     (Pillar 1, ~5 min)
# 2. cross_validation   (Pillar 1, ~1 min)
# 3. research_agent     (Pillar 2, ~5 min)
# 4. officer_scoring    (Pillar 2, ~1 min)
# 5. five_cs_scoring    (Pillar 3, ~2 min)
# 6. cam_generation     (Pillar 3, ~5 min)

# Use asyncio background tasks (FastAPI BackgroundTasks) or
# a simple in-memory job store (dict keyed by job_id)
# Frontend polls /status every 10 seconds and updates progress bar
```

---

### STEP 8 — Configuration & Environment

Create `backend/config.py` loading from `.env`:
```env
# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gpt-oss
OLLAMA_TIMEOUT_SECONDS=120

# AWS Textract fallback
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1

# External APIs
ECOURTS_API_KEY=
MCA21_API_KEY=
NEWS_API_KEY=
CIBIL_B2B_CLIENT_ID=
CIBIL_B2B_CLIENT_SECRET=

# Vivriti sector exposure caps (INR Crores)
SECTOR_CAP_NBFC=500
SECTOR_CAP_MANUFACTURING=200
SECTOR_CAP_TRADING=100
SECTOR_CAP_SERVICES=150

# App
MAX_UPLOAD_SIZE_MB=50
OCR_CONFIDENCE_THRESHOLD=70
CAM_OUTPUT_DIR=/tmp/cam_outputs
LOG_LEVEL=INFO
```

---

## CRITICAL CONSTRAINTS — READ BEFORE WRITING ANY CODE

1. **All Ollama calls MUST use `stream: false`** — the VM does not have enough RAM for streaming + full app stack simultaneously
2. **Ollama prompts must instruct the model to return ONLY JSON** for extraction tasks — no preamble, no markdown fences in the expected output path (strip them defensively anyway)
3. **All external API calls must have a 30-second timeout and graceful fallback** — if e-Courts is down, the research agent continues without it and flags the data as unavailable
4. **OCR pre-processing runs on CPU only** — do NOT use any CUDA/GPU code paths; the VM has no GPU
5. **DistilBERT must use CPU inference** — `device=-1` in all HuggingFace pipeline calls
6. **SHAP charts must save to `/tmp/` not to a mounted volume** — keep disk I/O minimal
7. **The CAM generator must complete within 10 minutes** — if Ollama section generation exceeds 8 minutes total, truncate remaining sections with a "[Section pending manual completion]" placeholder and still produce the document
8. **Never log borrower financial figures to stdout** — use structured logging that redacts INR amounts from log lines
9. **All API keys must come from environment variables** — never hardcode credentials in source files
10. **Python `asyncio` only — no `threading` or `multiprocessing`** — the FastAPI server runs single-process on this VM

---

## DELIVERABLE CHECKLIST

Before marking the build complete, verify each item:

- [ ] `docker compose up` starts all services cleanly
- [ ] `https://system.truvgo.tech` loads the Webtop desktop in a browser
- [ ] `/api/health` returns Ollama as reachable
- [ ] Upload a scanned PDF → OCR pipeline runs, confidence flags appear correctly
- [ ] Upload a GST JSON + ITR PDF → cross-validation checks run and flags are returned
- [ ] Research agent returns findings for a test CIN from at least 2 API sources
- [ ] Officer portal saves keyword-detected observations and adjusts C-scores
- [ ] Five Cs scorer produces a total score with grade
- [ ] CIBIL client returns a CMR rank and DPD history
- [ ] Loan limit calculator returns a value with the binding ceiling identified
- [ ] SHAP chart PNG is generated
- [ ] CAM generator produces a `.docx` and `.pdf` file with all sections
- [ ] Full end-to-end job completes within 30 minutes
- [ ] Frontend progress bar updates correctly through all 6 stages
- [ ] Download links on CAM preview screen work

---

## STARTING POINT

Begin with **Step 1** (docker-compose.yml and Nginx config). Confirm the infrastructure milestone before writing any application code. Then proceed sequentially through Steps 2–8.