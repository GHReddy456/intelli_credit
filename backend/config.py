"""
CreadON - Intelli-Credit Configuration
All thresholds, paths, and constants in one place.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_DIR  = BASE_DIR / "models" / "artifacts"
CAM_DIR    = BASE_DIR / "cam_outputs"

for _d in (UPLOAD_DIR, MODEL_DIR, CAM_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── LLM (optional - Ollama) ─────────────────────────────────────────────────
# phi3:mini is 3.8B params (~2.3 GB RAM), runs on CPU without a GPU.
# Alternatives (smaller/faster on CPU): qwen2:0.5b (394 MB), gemma3:1b (815 MB)
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL",    "phi3:mini")
USE_LLM           = os.getenv("USE_LLM", "false").lower() == "true"

# ── Financial Verification Thresholds ───────────────────────────────────────
GST_BANK_MISMATCH_THRESHOLD   = 0.15   # 15% tolerance
ITR_REVENUE_MISMATCH_THRESHOLD = 0.20  # 20% tolerance
GSTR2A_3B_MISMATCH_THRESHOLD  = 0.10   # 10% ITC mismatch
RELATED_PARTY_RPT_THRESHOLD   = 0.10   # 10% of revenue

# ── Fraud Detection ──────────────────────────────────────────────────────────
CIRCULAR_TRADING_THRESHOLD    = 0.80   # Hard reject above
BENFORD_CHI2_THRESHOLD        = 15.51  # p=0.05, df=8
ROUND_TRIP_DAYS               = 30     # Money returning within N days

# ── Credit Rule Engine ───────────────────────────────────────────────────────
DSCR_MIN                      = 1.10
ICR_MIN                       = 1.50
CURRENT_RATIO_MIN             = 1.20
DEBT_EQUITY_MAX               = 3.00
PROMOTER_RISK_HARD_REJECT     = 0.80
LITIGATION_SEVERITY_REJECT    = 0.75
COLLATERAL_COVERAGE_MIN       = 1.25

# ── Decision Engine ──────────────────────────────────────────────────────────
APPROVE_THRESHOLD             = 75     # credit_score >= 75 → APPROVE
CONDITIONAL_THRESHOLD         = 60     # credit_score >= 60 → CONDITIONAL
# Below CONDITIONAL_THRESHOLD  → REJECT

# ── Loan Pricing ─────────────────────────────────────────────────────────────
BASE_INTEREST_RATE            = 9.0    # % p.a.
RISK_PREMIUM_HIGH             = 3.0    # added for score < 65
RISK_PREMIUM_MEDIUM           = 1.5    # added for score 65-75
RISK_PREMIUM_LOW              = 0.5    # added for score > 75
LOAN_TO_TURNOVER_RATIO        = 0.40   # max loan = 40% of annual turnover

# ── Five Cs Weights (must sum to 1.0) ────────────────────────────────────────
FIVE_CS_WEIGHTS = {
    "character":   0.25,
    "capacity":    0.30,
    "capital":     0.20,
    "collateral":  0.15,
    "conditions":  0.10,
}

# ── Indian Sector Risk Scores (baseline) ─────────────────────────────────────
SECTOR_RISK = {
    # Existing
    "steel":          0.55,   # Cyclical, high capex, prone to Chinese dumping
    "textile":        0.50,   # Export-driven, FX risk, power-intensive
    "real_estate":    0.65,   # High leverage, regulatory delays, liquidity risk
    "it":             0.30,   # Resilient, high margins, low debt
    "pharma":         0.35,   # Regulated but stable, export demand
    "nbfc":           0.60,   # ALM risk, regulatory scrutiny, co-lending risks
    "infrastructure": 0.55,   # Execution risk, delayed receivables, government dependency
    "agri":           0.45,   # Monsoon risk, MSP dependency
    "auto":           0.50,   # EV transition risk, input cost volatility
    "cement":         0.45,   # Oligopoly, stable demand
    # New sectors
    "fmcg":           0.30,   # Resilient demand, strong brands, low leverage
    "energy":         0.50,   # Commodity price risk, stranded asset risk for fossil fuels
    "mining":         0.60,   # Regulatory risk, environmental litigation, cyclical
    "chemicals":      0.50,   # Specialty = low risk; commodity = high risk; midpoint
    "telecom":        0.55,   # Very high capex, spectrum debt, competitive intensity (Jio)
    "logistics":      0.40,   # Growing sector, formalisation trend, GST tailwind
    "default":        0.50,
}

# ── API Keys (loaded from .env) ──────────────────────────────────────────────
NEWSAPI_KEY       = os.getenv("NEWSAPI_KEY", "")
FINNHUB_KEY       = os.getenv("FINNHUB_KEY", "")
ALPHAVANTAGE_KEY  = os.getenv("ALPHAVANTAGE_KEY", "")

# ── Research ─────────────────────────────────────────────────────────────────
NEWS_LOOKBACK_DAYS            = 730    # 2 years
MAX_NEWS_ARTICLES             = 20
LITIGATION_KEYWORDS = [
    "NPA", "default", "NCLT", "insolvency", "DRT", "recovery",
    "fraud", "cheque bounce", "Section 138", "wilful defaulter",
    "ED raid", "CBI", "SEBI", "attachment order", "winding up",
]

# ── Feature Engine ────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    "revenue_growth_3yr",
    "ebitda_margin",
    "pat_margin",
    "debt_to_equity",
    "current_ratio",
    "interest_coverage_ratio",
    "dscr",
    "working_capital_days",
    "debtor_days",
    "inventory_days",
    "cashflow_volatility",
    "gst_bank_mismatch_score",
    "gstr2a_3b_mismatch_score",
    "itr_revenue_mismatch_score",
    "circular_trading_score",
    "benford_deviation_score",
    "litigation_count",
    "litigation_severity_score",
    "news_sentiment_score",
    "promoter_network_risk",
    "sector_risk_score",
    "collateral_coverage_ratio",
    "capacity_utilization",
    "customer_concentration",
    "regulatory_violation_count",
]

N_FEATURES = len(FEATURE_NAMES)  # 25
