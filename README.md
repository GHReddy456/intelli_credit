# Intelli-Credit — AI Credit Decisioning Engine

> **credON** · End-to-end AI-assisted credit appraisal for Indian corporate lending

Intelli-Credit automates the full credit underwriting workflow: upload a borrower's financial documents, receive a scored credit decision with a bank-format Credit Appraisal Memo (CAM) in under 2 minutes. Every verdict is traceable — from raw PDF text to the final recommendation.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Processing Pipeline — Phase by Phase](#3-processing-pipeline--phase-by-phase)
4. [Agents](#4-agents)
   - [Document Intelligence Agent](#41-document-intelligence-agent)
   - [Fraud Detection Agent](#42-fraud-detection-agent)
   - [Promoter Intelligence Agent](#43-promoter-intelligence-agent)
   - [Sector Intelligence Agent](#44-sector-intelligence-agent)
   - [Research Agent (Orchestrator)](#45-research-agent-orchestrator)
5. [Backend Modules](#5-backend-modules)
   - [Ingestion](#51-ingestion)
   - [Financial Verification](#52-financial-verification)
   - [Feature Engine](#53-feature-engine)
   - [Rule Engine](#54-rule-engine)
   - [Credit Model (ML)](#55-credit-model-ml)
   - [SHAP Explainability](#56-shap-explainability)
   - [Evidence Graph](#57-evidence-graph)
   - [Decision Engine](#58-decision-engine)
   - [CAM Generator + PDF Exporter](#59-cam-generator--pdf-exporter)
6. [API Reference](#6-api-reference)
7. [Frontend](#7-frontend)
8. [Configuration & Thresholds](#8-configuration--thresholds)
9. [LLM Integration (Optional)](#9-llm-integration-optional)
10. [Setup & Running](#10-setup--running)
11. [Project Structure](#11-project-structure)
12. [Key Design Decisions](#12-key-design-decisions)

---

## 1. Project Overview

| Dimension | Detail |
|-----------|--------|
| **Domain** | Indian corporate credit underwriting (MSME / Mid-corporate) |
| **Stack** | FastAPI (backend) · React 18 (frontend) · XGBoost (ML) · NetworkX (graphs) |
| **LLM** | Optional Ollama integration (`phi3:mini` by default) — degrades gracefully to rule-based fallback |
| **Output** | Credit score (0–100), risk grade (AAA–D), loan recommendation, PD estimate, SHAP attribution, network graphs, and a bank-format PDF CAM |
| **Latency** | Full pipeline run: ~30–90 s (depending on document count and LLM usage) |

The engine accepts any combination of:
- Annual Reports / Audited Financials (PDF)
- Bank Statements (PDF / CSV)
- GST Returns (GSTR-1, 2A, 3B as PDF or Excel)
- Income Tax Returns (ITR PDF)
- MCA filings, charge documents, MOA/AOA

---

## 2. System Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        React 18 Frontend (port 3000)                      │
│  Upload → Dashboard → Decision → Fraud Graph → Promoter → Agents →        │
│           Evidence → CAM PDF                                               │
└──────────────────────────────┬────────────────────────────────────────────┘
                               │ REST (JSON) + File upload
┌──────────────────────────────▼────────────────────────────────────────────┐
│                       FastAPI Backend (port 8000)                          │
│  /api/upload  /api/status/{id}  /api/analysis/{id}  /api/cam/{id}/download│
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                     Async Pipeline Orchestrator                      │ │
│  │  (asyncio.create_task → thread pool via asyncio.to_thread)           │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Phase 1   Phase 2   Phase 3   Phase 4   Phase 5   Phase 6   Phase 7      │
│  Ingest  → Verify  → Research→  Agents →  Features→ Rules+ML→  SHAP       │
│                                                                            │
│  Phase 8   Phase 9   Phase 10                                              │
│  Decision→  CAM PDF →  Assemble Result & Graphs                            │
│                                                                            │
│  Job Store: file-backed pickle (uploads/jobs/*.pkl)                        │
└───────────────────────────────────────────────────────────────────────────┘
```

**Job lifecycle:**
1. `POST /api/upload` creates a job record and returns a `job_id` immediately.
2. The pipeline runs asynchronously in a thread pool (keeps the event loop free).
3. Frontend polls `GET /api/status/{job_id}` (5 s interval) watching `progress` 0–100.
4. On `done`, frontend fetches `GET /api/analysis/{job_id}` for the full result JSON.
5. `GET /api/cam/{job_id}/download` streams the generated PDF.

Jobs persist across server restarts via `.pkl` files in `uploads/jobs/`.

---

## 3. Processing Pipeline — Phase by Phase

```
Document Files (PDF/Excel/CSV)
        │
        ▼ Phase 1 — Document Processing (progress 5 → 20)
   ┌────────────┐    ┌──────────┐    ┌───────────────────┐    ┌───────────────┐
   │ PDFParser  │───▶│OCREngine │───▶│DocumentSegmenter  │───▶│TableExtractor │
   │ (pdfminer) │    │(pytess-  │    │(section labelling)│    │(pandas/camelot│
   └────────────┘    │ eract)   │    └───────────────────┘    └───────────────┘
                     └──────────┘
        │                              │                              │
        ▼ Phase 2 — Financial Verification (20 → 35)                 │
   ┌────────────────────────────┐                                     │
   │ FinancialConsistencyEngine │◀────────────────────────────────────┘
   │ • GST vs Bank mismatch     │ (cross-checks segmented docs against tables)
   │ • GSTR-2A vs 3B ITC check  │
   │ • ITR revenue reconcile    │
   └────────────────────────────┘
        │
        ▼ Phase 3 — Research (35 → 50)
   ┌──────────────────────────────────────────────────────────────────┐
   │ ResearchAgent (parallel threads)                                 │
   │   • NewsScraper       — sentiment from headlines                 │
   │   • LitigationDetector— court case signals in docs / news        │
   │   • MCAParser         — director list, charges, filings          │
   │   • SectorAnalyzer    — sector risk + regulatory mentions        │
   └──────────────────────────────────────────────────────────────────┘
        │
        ▼ Phase 4 — AI Agents (50 → 65)
   ┌─────────────────────────┐  ┌──────────────────────┐
   │DocumentIntelligenceAgent│  │FraudDetectionAgent   │
   │ audit flags, governance │  │ circular trading,    │
   │ going concern, RPTs     │  │ Benford, shell cos.  │
   └─────────────────────────┘  └──────────────────────┘
   ┌─────────────────────────┐  ┌──────────────────────┐
   │PromoterIntelligenceAgent│  │SectorIntelligenceAgent│
   │ NetworkX risk graph     │  │ sector conditions    │
   │ shell network detection │  │ headwinds/tailwinds  │
   └─────────────────────────┘  └──────────────────────┘
        │
        ▼ Phase 5 — Feature Engineering (65 → 75)
   25 numerical features extracted (revenue growth, EBITDA margin,
   D/E, DSCR, GST mismatch, fraud scores, promoter risk, …)
        │
        ▼ Phase 6 — Rule Engine + XGBoost ML (75 → 85)
   Hard-reject rules checked first → if triggered, ML bypassed.
   XGBoost predicts probability of default → credit score (0–100).
        │
        ▼ Phase 7 — SHAP Explainability (85 → 90)
   Feature attributions ranked by contribution magnitude.
        │
        ▼ Phase 8 — Decision Engine (90 → 95)
   Verdict: APPROVE / CONDITIONAL_APPROVE / REJECT
   Loan amount, interest rate, conditions, risk grade, PD.
        │
        ▼ Phase 9 — CAM Generation + PDF Export (95 → 100)
   11-section CAM assembled → rendered to PDF via ReportLab.
        │
        ▼ Phase 10 — Result Assembly
   Full JSON (scores, graphs, agent reports, evidence) → stored in job.
```

---

## 4. Agents

### 4.1 Document Intelligence Agent

**File:** `agents/document_intelligence_agent.py`

**Purpose:** Performs structured, keyword-directed analysis over every section of every uploaded document to extract qualitative risk signals that numerical financial ratios cannot capture.

**What it does:**

1. **Audit Red Flag Detection** — Scans all document sections for 8 classes of critical auditor signals:

   | Flag | Trigger Keywords | Severity |
   |------|-----------------|---------|
   | `going_concern` | "going concern", "material uncertainty", "doubt about ability" | HIGH |
   | `qualified_opinion` | "qualified opinion", "except for", "qualification" | HIGH |
   | `adverse_opinion` | "adverse opinion" | HIGH |
   | `emphasis_of_matter` | "emphasis of matter" | MEDIUM |
   | `scope_limitation` | "unable to obtain", "scope limitation" | MEDIUM |
   | `fraud_suspicion` | "suspected fraud", "forensic", "management override" | MEDIUM |
   | `related_party_excess` | "related party transactions", "arm's length", "RPT" | MEDIUM |
   | `contingent_large` | "contingent liabilities" | MEDIUM |

2. **Governance Flag Detection** — Additionally scans for 4 categories of corporate governance warnings:

   | Flag | Trigger Keywords |
   |------|----------------|
   | `promoter_pledge` | "pledge", "pledged shares" |
   | `board_dispute` | "resignation of director", "reconstitution", "removed from board" |
   | `auditor_change` | "change of auditor", "resigned as auditor" |
   | `regulatory_show_cause` | "show cause notice", "demand notice", "regulatory action" |

3. **Key Financial Findings** — Collects structured financial figures from each document's segment summary for cross-document comparison.

4. **LLM Enrichment (optional)** — If Ollama is running, generates a natural-language qualitative summary of all audit findings.

5. **Deduplication** — Identical flag types from the same or multiple documents are deduplicated by flag name.

**Output:**
```json
{
  "audit_flags": [...],
  "governance_flags": [...],
  "key_findings": [...],
  "section_summaries": {...},
  "llm_summary": "...",
  "high_severity_count": 2,
  "overall_doc_risk": "HIGH | MEDIUM | LOW"
}
```

**Risk classification:** `overall_doc_risk` = HIGH if any HIGH-severity audit flag exists, MEDIUM if any flag exists, LOW otherwise.

---

### 4.2 Fraud Detection Agent

**File:** `agents/fraud_detection_agent.py`

**Purpose:** Aggregates all financial fraud signals into a single composite `fraud_risk_score` (0–100). Triggers a hard reject when circular trading evidence is overwhelming.

**What it does:**

1. **Circular Trading Detection** (`fraud/circular_trading_detector.py`) — Builds a directed transaction graph from bank statement data, detects cycles (NetworkX cycle detection), identifies shell entities (fuzzy name matching against known counterparties), and finds layered/reciprocal payment pairs. Sub-scores:
   - `circular_trading_score` — proportion of transaction volume involved in detected cycles
   - `layered_score` — round-trip ratio of suspicious pairs
   - `shell_score` — share of counterparties matching shell entity patterns

2. **Benford's Law Analysis** (`fraud/benford_analyzer.py`) — Extracts all monetary figures from financial statements and tests whether the leading-digit distribution conforms to Benford's Law using a chi-squared test (chi² > 15.51 at p=0.05 with df=8 → high deviation score). Deviations indicate possible fabricated or manipulated figures.

3. **GST/Bank Mismatch Signals** — Pulls pre-computed mismatch scores from the `FinancialConsistencyEngine`:
   - `gst_bank_mismatch_score` — GST-declared turnover vs. bank credit inflows
   - `gstr2a_3b_mismatch_score` — ITC claimed in GSTR-3B vs. available in GSTR-2A

4. **Bank Anomaly Detection** — Scans bank statement data and document text for large round-number transfers, unusual intra-day patterns, and concentration in a single counterparty.

5. **Audit Remark Scoring** — Converts qualitative auditor remarks (qualified opinion, going concern, scope limitation) into a continuous risk score.

**Weighted composite formula:**

| Signal | Weight |
|--------|--------|
| Circular trading score | 30% |
| Benford deviation | 18% |
| GST-Bank mismatch | 17% |
| GSTR-2A/3B mismatch | 12% |
| Audit remark score | 10% |
| Bank anomaly score | 8% |
| Layered transactions | 3% |
| Shell entities | 2% |

**Hard reject trigger:** `circular_trading_score > 0.80` OR composite `fraud_risk_score > 0.85`.

**Output:**
```json
{
  "fraud_risk_score": 34.2,
  "fraud_risk_normalized": 0.342,
  "circular_trading": { "top_cycles": [...], "shell_entities": [...] },
  "benford": { "benford_deviation_score": 0.12, "flags": [...] },
  "bank_anomaly_score": 0.05,
  "is_hard_reject": false,
  "all_flags": [...]
}
```

---

### 4.3 Promoter Intelligence Agent

**File:** `agents/promoter_intelligence_agent.py`

**Purpose:** Constructs a promoter risk network using the NetworkX graph library, quantifies relationship complexity and governance risk, and detects shell company networks behind the borrower.

**What it does:**

1. **Promoter Network Graph Construction** — Builds a directed graph with four node types:
   - `promoter` — identified from document text (regex extraction)
   - `director` — from MCA director list
   - `litigation` — each court case as a node linked to involved promoters
   - `lender` — companies with existing charge/loan relationships (from MCA company charges)

   Edges carry relationship labels: `is_director`, `involved_in`, `borrowed_from`.

2. **Risk Scoring** — Scores the network based on:
   - Number of active litigation nodes
   - Litigation severity (HIGH/MEDIUM/LOW flag weights)
   - Director count relative to company size
   - Existing charge/lender concentration

3. **Shell Company Network Detection** — Identifies two structural red flags:
   - **Multi-company directors**: Any director appearing in 3 or more companies suggests possible shell network involvement.
   - **Shared registered address**: Multiple companies at the identical address indicate potential related-party obfuscation.

   The `shell_network_score` is added (weighted 30%) to the base promoter risk score.

4. **Graph Serialization** — Exports the NetworkX graph as node/edge JSON for the React D3 force-directed graph visualization in the frontend.

**Output:**
```json
{
  "promoter_network_risk": 0.42,
  "shell_network_score": 0.15,
  "multi_company_directors": [...],
  "promoter_count": 2,
  "director_count": 5,
  "litigation_links": 1,
  "graph_nodes": 12,
  "graph_edges": 8,
  "graph_data": { "nodes": [...], "links": [...] },
  "flags": [...]
}
```

---

### 4.4 Sector Intelligence Agent

**File:** `agents/sector_intelligence_agent.py`

**Purpose:** Synthesizes sector-level macro-risk into a single `sector_risk_score` and produces a human-readable conditions narrative, incorporating RBI/SEBI regulatory headwinds and recent news tailwinds.

**What it does:**

1. **Sector Risk Baseline** — Uses a pre-configured baseline risk table (`config/settings.py`) covering 20+ Indian industry segments with calibrated base scores reflecting structural sector risk (e.g., real estate 0.65, IT 0.30, steel 0.55).

2. **Regulatory Adjustment** — Each regulatory mention from news or filings adds +0.05 to the baseline score, capped at a maximum adjustment of +0.15. This captures recent headwinds (GST notices, SEBI show-causes, RBI norms).

3. **Headwinds/Tailwinds Extraction** — Summarizes up to 3 regulatory headwinds (from `regulatory_mentions`) and up to 3 positive tailwinds (from news articles with `POSITIVE` sentiment).

4. **Conditions Narrative** — If Ollama is available, generates a focused 2-sentence LLM-written sector outlook specific to the Indian context (mentioning RBI, SEBI, PLI, GST as relevant). Falls back to a deterministic template.

**Output:**
```json
{
  "sector": "steel",
  "sector_risk_score": 0.60,
  "sector_outlook": "NEGATIVE",
  "regulatory_violation_count": 2,
  "headwinds": ["Anti-dumping duty review...", ...],
  "tailwinds": ["PLI scheme disbursements...", ...],
  "conditions_summary": "The Steel sector outlook is NEGATIVE..."
}
```

---

### 4.5 Research Agent (Orchestrator)

**File:** `research/research_agent.py`

**Purpose:** Orchestrates all external research modules in parallel threads and aggregates their outputs into a unified research report consumed by the AI agents and Feature Engine.

**What it does:**

1. **Promoter Name Extraction** — Parses document text with regex patterns to identify up to 5 named promoters/directors (looks for titles like "Managing Director", "Chairman", "CEO" followed by proper names).

2. **Parallel Research Execution** — Spins up 4 parallel threads:

   | Thread | Module | What it finds |
   |--------|--------|---------------|
   | T1 | `NewsScraper` | Recent headlines, assigns POSITIVE/NEGATIVE/NEUTRAL sentiment, computes aggregate `news_sentiment_score` |
   | T2 | `MCAParser` | Director list, company charges, MCA filing status, registered address |
   | T3 | `LitigationDetector` | Court case mentions (DRT, NCLT, High Court) from documents and news; severity classification |
   | T4 | `SectorAnalyzer` | Sector identification, baseline risk score, regulatory mentions |

   Note: Litigation and Sector analysis start after news completes (they consume news results), so the actual execution is a 2-wave parallel: T1+T2 → T3+T4.

3. **Research Risk Score** — Combines:
   ```
   research_risk = (1 - news_sentiment) × 0.30
                 + litigation_severity  × 0.50
                 + sector_risk          × 0.20
   ```

**Output (flat + nested):**
```json
{
  "company_name": "...",
  "promoter_names": ["..."],
  "news": { "articles": [...], "news_sentiment_score": 0.45 },
  "litigation": { "cases": [...], "litigation_count": 2, "litigation_severity_score": 0.3 },
  "mca": { "director_list": [...], "company_charges": [...] },
  "sector": { "sector": "auto", "sector_risk_score": 0.50 },
  "research_risk_score": 0.38
}
```

---

## 5. Backend Modules

### 5.1 Ingestion

| Module | File | Responsibility |
|--------|------|---------------|
| `PDFParser` | `ingestion/pdf_parser.py` | Extracts text, metadata, and page count from PDF using `pdfminer`. Assigns `doc_type` (annual_report, bank_statement, itr, gst_return, etc.) from filename and content heuristics. Reports `extraction_confidence` 0–1. |
| `OCREngine` | `ingestion/ocr_engine.py` | Invoked when `PDFParser` confidence < 0.40 (scanned/image PDFs). Uses `pytesseract` + `pdf2image` to extract text via OCR. |
| `DocumentSegmenter` | `ingestion/document_segmenter.py` | Splits parsed text into labeled sections (Balance Sheet, P&L, Cash Flow, Audit Report, Directors' Report, etc.) using heading patterns. Computes `word_count` and `flags` per section. |
| `TableExtractor` | `ingestion/table_extractor.py` | Extracts tabular data from PDFs (via `camelot`/`pdfplumber`) and spreadsheets (via `pandas`). Returns list of table dicts with headers and rows. |
| `NumericNormalizer` | `ingestion/numeric_normalizer.py` | Converts Indian numeric formats (lakhs, crores, commas) to float. |

**Confidence fallback:** If a parsed document has text content > 200 chars but low confidence, confidence is floored at 0.60 to avoid spurious OCR re-runs.

---

### 5.2 Financial Verification

**File:** `verification/financial_consistency_engine.py`

Cross-validates financial data across documents to detect inconsistencies that may indicate window dressing or fraud:

| Check | Method | Threshold |
|-------|--------|-----------|
| **GST vs Bank** | Compares GST-declared turnover with net bank credit inflows | 15% tolerance |
| **GSTR-2A vs 3B** | Compares ITC available (2A) vs ITC claimed (3B) | 10% tolerance |
| **ITR Revenue** | Compares ITR-declared income vs financial statement revenue | 20% tolerance |

Produces `mismatch_scores` (0–1 for each check) consumed by both the Fraud Detection Agent and the Feature Engine.

---

### 5.3 Feature Engine

**File:** `features/feature_engine.py`

Computes exactly **25 numerical features** from all upstream outputs, forming the ML model's input vector. Missing financial data is imputed to population medians.

| # | Feature | Source |
|---|---------|--------|
| 1 | `revenue_growth_3yr` | 3-year revenue CAGR from P&L tables |
| 2 | `ebitda_margin` | EBITDA / Revenue |
| 3 | `pat_margin` | PAT / Revenue |
| 4 | `debt_to_equity` | Total Debt / Equity |
| 5 | `current_ratio` | Current Assets / Current Liabilities |
| 6 | `interest_coverage_ratio` | EBIT / Interest Expense |
| 7 | `dscr` | Net Cash from Operations / Total Debt Service |
| 8 | `working_capital_days` | (WC / Revenue) × 365 |
| 9 | `debtor_days` | (Receivables / Revenue) × 365 |
| 10 | `inventory_days` | (Inventory / COGS) × 365 |
| 11 | `cashflow_volatility` | Std dev of annual CFO / mean CFO |
| 12 | `gst_bank_mismatch_score` | From FinancialConsistencyEngine |
| 13 | `gstr2a_3b_mismatch_score` | From FinancialConsistencyEngine |
| 14 | `itr_revenue_mismatch_score` | From FinancialConsistencyEngine |
| 15 | `circular_trading_score` | From FraudDetectionAgent |
| 16 | `benford_deviation_score` | From FraudDetectionAgent |
| 17 | `promoter_network_risk` | From PromoterIntelligenceAgent |
| 18 | `litigation_severity_score` | From ResearchAgent |
| 19 | `news_sentiment_score` | From ResearchAgent |
| 20 | `sector_risk_score` | From SectorIntelligenceAgent |
| 21 | `regulatory_violation_count` | From ResearchAgent |
| 22 | `collateral_coverage_ratio` | Collateral Value / Loan Amount |
| 23 | `capacity_utilization` | Extracted from Directors' Report |
| 24 | `customer_concentration` | Revenue from top customer / Total Revenue |
| 25 | `dd_risk_score` | Analyst due diligence notes → keyword risk score |

---

### 5.4 Rule Engine

**File:** `rules/rule_engine.py`

Deterministic credit policy rules applied **before** the ML model. Hard reject rules short-circuit the entire ML scoring pipeline.

**Hard Reject Rules** (immediate rejection regardless of ML score):

| Rule | Condition | Severity |
|------|-----------|---------|
| Circular trading | Score > 0.80 | CRITICAL |
| Promoter network risk | Score > 0.80 | CRITICAL |
| Litigation severity | Score > 0.75 | CRITICAL |
| DSCR | < 1.10 | HIGH |

**Policy Rules** (score deductions, 5–15 points each):

| Rule | Condition | Deduction |
|------|-----------|----------|
| Current ratio | < 1.20 | 10 pts |
| Interest coverage | < 1.50 | 12 pts |
| Debt-to-equity | > 3.00 | 15 pts |
| GST-Bank mismatch | > 30% | 10 pts |
| GSTR-2A/3B mismatch | > 20% | 8 pts |
| Benford deviation | > 0.50 | 8 pts |
| Collateral coverage | < 1.25× | 10 pts |
| Capacity utilization | < 40% | 5 pts |
| Negative news sentiment | > 0.70 | 7 pts |
| Regulatory violations | > 3 | 6 pts |
| ITR-revenue mismatch | > 20% | 10 pts |
| Debtor days | > 90 days | 8 pts |
| PAT margin | < 0% | 10 pts |

---

### 5.5 Credit Model (ML)

**File:** `models/credit_model.py`

An **XGBoost classifier** trained on a synthetic Indian corporate credit dataset (2,000 samples) calibrated to reflect realistic SME default characteristics.

**Training approach:**
- Features are preprocessed through a scikit-learn pipeline (`models/feature_pipeline.py`) with StandardScaler and median imputation.
- Model is trained with cross-validation; AUC, F1, precision, recall saved to `models/artifacts/model_metrics.json`.
- Model and pipeline artifacts are persisted to disk; subsequent runs load from disk rather than re-training.

**Prediction:**
- Returns `probability_of_default` (0–1) → converted to `credit_score` = `(1 - PD) × 100`.
- **Confidence interval** computed via 10-sample bootstrap perturbation (±1.5% gaussian noise on features), reported as `score_ci_low` / `score_ci_high` at 95% confidence.

**Risk Grade table:**

| Score | Grade | PD midpoint |
|-------|-------|------------|
| ≥ 90 | AAA | 0.5% |
| ≥ 80 | AA | 1.5% |
| ≥ 75 | A | 3.0% |
| ≥ 70 | BBB | 6.0% |
| ≥ 65 | BB | 11.0% |
| ≥ 60 | B | 18.0% |
| ≥ 50 | C | 30.0% |
| < 50 | D | 50.0% |

---

### 5.6 SHAP Explainability

**File:** `explainability/shap_explainer.py`

Uses the SHAP (SHapley Additive exPlanations) library with the XGBoost model's tree explainer to compute the contribution of each feature to the individual credit score prediction.

- Produces a ranked list of features sorted by absolute SHAP value (most impactful first).
- The top contributors are shown in the frontend's Decision Panel as a waterfall/bar chart.
- Colors: positive SHAP (pushes toward approval) shown green; negative SHAP (pushes toward rejection) shown red.

---

### 5.7 Evidence Graph

**File:** `explainability/evidence_graph.py`

Builds a directed acyclic graph tracing the evidence chain from raw documents to the final decision, serialized as node-link JSON for the React `EvidenceViewer` component.

**Graph layers (5 levels):**

```
Layer 0:  DECISION node (color-coded: green/amber/red)
    ▲
Layer 1:  Feature nodes (25 features, color by SHAP importance)
    ▲
Layer 2:  Rule/Finding nodes (rule violations, key findings)
    ▲
Layer 3:  Segment nodes (document sections: P&L, Balance Sheet, etc.)
    ▲
Layer 4:  Document nodes (uploaded files)
```

Each feature node carries metadata about which document type it came from (e.g., `debt_to_equity` ← Annual Report → Balance Sheet), making the reasoning auditable end-to-end.

---

### 5.8 Decision Engine

**File:** `decision/decision_engine.py`

Combines `rule_result` (deterministic) + `ml_result` (probabilistic) into the final credit verdict, loan structuring recommendation, and conditions.

**Blended score computation:**
```
blended_score = rule_adjusted_score × 0.60 + credit_score × 0.40
```
(If hard reject triggered, verdict is REJECT regardless of ML score.)

**Verdict thresholds:**

| Verdict | Condition |
|---------|-----------|
| `APPROVE` | blended_score ≥ 75 |
| `CONDITIONAL_APPROVE` | blended_score ≥ 60 |
| `REJECT` | blended_score < 60 or hard reject rule triggered |

**Loan structuring:**
- **Recommended loan amount:** min(40% of annual turnover, collateral value / 1.25)
- **Interest rate:** Base rate (9.0% p.a.) + risk premium by grade (AAA: +0%, ..., D: +5.00%)

**Conditions (for CONDITIONAL_APPROVE):** The engine maps triggered policy rules to specific pre-approval conditions, e.g.:
- Low DSCR → "require additional security / step-down EMI structure"
- GST mismatch → "post audited financials for last 3 years"
- High D/E → "promoter equity infusion required before first drawdown"

**Five Cs scoring:**

| C | Weight | Key inputs |
|---|--------|-----------|
| Character | 25% | Audit flags, governance flags, litigation, news sentiment |
| Capacity | 30% | DSCR, ICR, EBITDA margin, revenue growth |
| Capital | 20% | D/E, PAT margin, equity adequacy |
| Collateral | 15% | Collateral coverage ratio |
| Conditions | 10% | Sector risk, regulatory violations |

---

### 5.9 CAM Generator + PDF Exporter

**Files:** `cam/cam_generator.py`, `cam/pdf_exporter.py`

**CAM Generator** assembles an 11-section Credit Appraisal Memo dictionary following Indian bank CAM format:

| Section | Content |
|---------|---------|
| 1. Executive Summary | Verdict, credit score, grade, recommended amount & rate |
| 2. Borrower Profile | Company details, promoters, MCA status, sector |
| 3. Facility Structure | Loan purpose, amount, tenure, security, rate |
| 4. Five Cs Analysis | Character/Capacity/Capital/Collateral/Conditions scored |
| 5. Financial Ratios | All 25 features with industry benchmarks |
| 6. Fraud & Integrity Assessment | Fraud score, circular trading findings, Benford results |
| 7. Promoter & Governance | Network risk, litigation, shell entity flags |
| 8. Sector Outlook | Sector risk, headwinds, tailwinds, regulatory environment |
| 9. AI Risk Attribution | SHAP waterfall — top 10 feature contributors |
| 10. Evidence Traceability | Feature → source document mapping |
| 11. Sanction Recommendation | Conditions precedent, monitoring covenants |

**PDF Exporter** renders the CAM dict to a formatted PDF using ReportLab with:
- Bank-style header and footer with page numbers
- Color-coded verdict banner (green/amber/red)
- SHAP bar chart embedded as vector graphics
- Tables for financial ratios with peer benchmarks

Output path: `cam_outputs/{job_id}_CAM.pdf`

---

## 6. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload documents. Form fields: `files[]`, `company_name`, `due_diligence_notes`. Returns `{job_id}`. |
| `GET` | `/api/status/{job_id}` | Poll pipeline progress. Returns `{status, progress 0–100, error}`. |
| `GET` | `/api/analysis/{job_id}` | Full result JSON (only when status=`done`). |
| `HEAD` | `/api/cam/{job_id}/download` | Check if PDF is ready (200 / 404). |
| `GET` | `/api/cam/{job_id}/download` | Stream CAM PDF. |
| `GET` | `/api/health` | Health check: `{status: "ok"}`. |
| `GET` | `/api/model/metrics` | XGBoost training metrics (AUC, F1, etc.). |
| `GET` | `/api/llm/config` | Current LLM device and model. |
| `POST` | `/api/llm/config` | Toggle LLM device: `{device: "cpu" | "gpu"}`. |

**Pipeline status values:**

```
queued → parsing_documents → verifying_financials → running_research →
running_agents → computing_features → scoring → explaining →
deciding → generating_cam → done
```

---

## 7. Frontend

**Stack:** React 18 · Create React App · Inline styles · D3.js (network graphs) · Recharts (bar/radar charts)

**Component map:**

| Component | Tab | Description |
|-----------|-----|-------------|
| `HomePage` | — | Landing page with product introduction |
| `UploadPage` | — | Multi-file drag-and-drop upload with company name input |
| `Dashboard` | Dashboard | Overview metrics: credit score, grade, PD, fraud score, DSCR, D/E, sector risk, promoter risk |
| `DecisionPanel` | Decision | Verdict banner, recommended loan, rate, conditions, SHAP waterfall, stress test |
| `FraudGraph` | Fraud Intel | D3 force-directed graph of transaction counterparties (cycles in red, shell entities in amber) |
| `PromoterGraph` | Promoter Intel | D3 force-directed graph of promoter → director → litigation → lender network |
| `AgentReports` | Agent Reports | Tabbed view: Audit flags, governance flags, key findings, news, sector summary |
| `EvidenceViewer` | Evidence | Interactive 5-layer evidence graph (document → segment → feature → finding → decision) |
| `CAMViewer` | CAM PDF | Download + inline preview of generated PDF |
| `LLMSelector` | (header) | Toggle between CPU/GPU for Ollama LLM |

**Theme:**
- Body background: `#080402` (near-black)
- Glass cards: `rgba(34,22,16,0.82)` warm dark brown with backdrop blur
- Accent: `#ec5b13` orange
- Text: `#f1f5f9` primary · `rgba(255,255,255,0.5)` secondary
- Verdict colors: `#10b981` green (approve) · `#f59e0b` amber (conditional) · `#ef4444` red (reject)

---

## 8. Configuration & Thresholds

All thresholds are centralized in `backend/config.py` and can be overridden via environment variables:

```python
# LLM
OLLAMA_BASE_URL   = "http://localhost:11434"   # env: OLLAMA_BASE_URL
OLLAMA_MODEL      = "phi3:mini"                # env: OLLAMA_MODEL
USE_LLM           = False                      # env: USE_LLM=true

# Verification thresholds
GST_BANK_MISMATCH_THRESHOLD    = 0.15   # 15%
ITR_REVENUE_MISMATCH_THRESHOLD = 0.20   # 20%
GSTR2A_3B_MISMATCH_THRESHOLD   = 0.10   # 10%

# Credit rules
DSCR_MIN                  = 1.10
ICR_MIN                   = 1.50
CURRENT_RATIO_MIN         = 1.20
DEBT_EQUITY_MAX           = 3.00
COLLATERAL_COVERAGE_MIN   = 1.25

# Decision thresholds
APPROVE_THRESHOLD         = 75    # score >= 75 → APPROVE
CONDITIONAL_THRESHOLD     = 60    # score >= 60 → CONDITIONAL_APPROVE

# Pricing
BASE_INTEREST_RATE        = 9.0   # % p.a.
LOAN_TO_TURNOVER_RATIO    = 0.40  # max loan = 40% of turnover

# Fraud
CIRCULAR_TRADING_THRESHOLD = 0.80  # hard reject above
BENFORD_CHI2_THRESHOLD     = 15.51 # p=0.05, df=8
```

---

## 9. LLM Integration (Optional)

The system uses **Ollama** for optional LLM enrichment. When Ollama is not running or `USE_LLM=false`, every LLM call gracefully falls back to a deterministic rule-based equivalent.

**LLM is used in:**
- `DocumentIntelligenceAgent` — qualitative audit finding summary
- `SectorIntelligenceAgent` — sector conditions narrative
- `DecisionEngine` — natural language explanation of decision rationale

**Recommended models (CPU-runnable):**

| Model | Size | Notes |
|-------|------|-------|
| `phi3:mini` | ~2.3 GB | Default. Good quality, runs on 8 GB RAM |
| `qwen2:0.5b` | ~394 MB | Fastest, minimal RAM |
| `gemma3:1b` | ~815 MB | Good balance of speed and quality |

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull phi3:mini

# Enable LLM in env
export USE_LLM=true
```

---

## 10. Setup & Running

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- Tesseract OCR (for scanned PDFs)

### Backend Setup

```bash
# Clone and enter project
cd credON_new

# Install Python dependencies
pip install -r requirements.txt

# Start backend (auto-trains ML model on first run)
python run.py

# Options:
python run.py --demo    # generate sample demo documents first
python run.py --train   # force-retrain ML model
```

Backend starts at `http://localhost:8000`.  
Interactive API docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm start           # dev server on port 3000
npm run build       # production build → frontend/build/
```

### Production (combined)

The FastAPI backend serves the React production build as static files. Build the frontend first, then `python run.py` serves everything from port 8000.

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_LLM` | `false` | Enable Ollama LLM enrichment |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `phi3:mini` | Model to use for inference |

---

## 11. Project Structure

```
credON_new/
├── run.py                          # Entry point — CLI with --demo, --train flags
├── requirements.txt
│
├── backend/
│   ├── main.py                     # FastAPI app, job store, pipeline orchestrator
│   ├── config.py                   # All thresholds and constants
│   └── llm.py                      # Ollama client wrapper (safe fallback)
│
├── ingestion/
│   ├── pdf_parser.py               # Text extraction + doc type classification
│   ├── ocr_engine.py               # Tesseract OCR for scanned PDFs
│   ├── document_segmenter.py       # Section labeling (P&L, BS, Audit, etc.)
│   ├── table_extractor.py          # Tabular data extraction (camelot/pdfplumber)
│   └── numeric_normalizer.py       # Indian number format → float
│
├── verification/
│   └── financial_consistency_engine.py   # GST/Bank/ITR cross-validation
│
├── research/
│   ├── research_agent.py           # Parallel orchestrator (news + MCA + litig + sector)
│   ├── news_scraper.py             # Headline scraping + sentiment scoring
│   ├── litigation_detector.py      # Court case detection (DRT, NCLT, HC)
│   ├── mca_parser.py               # MCA director/charge data extraction
│   └── sector_analyzer.py          # Sector identification + risk baseline
│
├── agents/
│   ├── document_intelligence_agent.py    # Audit & governance flag extraction
│   ├── fraud_detection_agent.py          # Composite fraud score (8 signals)
│   ├── promoter_intelligence_agent.py    # NetworkX promoter risk graph
│   └── sector_intelligence_agent.py      # Sector conditions synthesizer
│
├── fraud/
│   ├── circular_trading_detector.py      # Transaction cycle detection
│   ├── benford_analyzer.py               # Benford's Law chi-squared test
│   └── transaction_graph.py              # Graph utilities
│
├── features/
│   └── feature_engine.py           # 25-feature vector computation
│
├── rules/
│   └── rule_engine.py              # Deterministic hard-reject + policy rules
│
├── models/
│   ├── credit_model.py             # XGBoost classifier + bootstrap CI
│   ├── feature_pipeline.py         # sklearn preprocessing pipeline
│   └── artifacts/                  # Saved model, pipeline, metrics (auto-generated)
│
├── explainability/
│   ├── shap_explainer.py           # SHAP tree explainer for XGBoost
│   └── evidence_graph.py           # 5-layer document→decision traceability graph
│
├── decision/
│   └── decision_engine.py          # Verdict + loan structuring + Five Cs
│
├── cam/
│   ├── cam_generator.py            # 11-section CAM content assembly
│   └── pdf_exporter.py             # ReportLab PDF rendering
│
├── graphs/
│   ├── promoter_network_graph.py   # NetworkX graph serializers
│   └── transaction_graph_visualizer.py
│
├── config/
│   ├── prompts.py                  # LLM prompt templates
│   └── settings.py                 # Sector risk table, feature names
│
├── cam_outputs/                    # Generated PDF CAMs
├── uploads/                        # Uploaded documents + job pkl store
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── Dashboard.jsx
    │   │   ├── DecisionPanel.jsx
    │   │   ├── FraudGraph.jsx
    │   │   ├── PromoterGraph.jsx
    │   │   ├── AgentReports.jsx
    │   │   ├── EvidenceViewer.jsx
    │   │   ├── CAMViewer.jsx
    │   │   ├── LLMSelector.jsx
    │   │   ├── UploadPage.jsx
    │   │   ├── HomePage.jsx
    │   │   └── RiskRadar.jsx
    │   └── App.jsx
    └── public/
        └── index.html              # CSS theme variables (bg, card, accent colors)
```

---

## 12. Key Design Decisions

**1. Hard rejects bypass ML entirely.**
When circular trading score > 0.80, promoter risk > 0.80, or litigation severity > 0.75 is detected, the system rejects immediately without running the XGBoost model. This ensures deterministic enforcement of credit policy irrespective of model uncertainty.

**2. LLM is always optional.**
Every LLM call in the codebase is wrapped in an `ollama_available()` guard with a deterministic fallback. The system produces identical structured outputs whether or not an LLM is running.

**3. 60/40 rule-vs-ML blending.**
The final blended score weights rule-adjusted score at 60% and ML score at 40%. This prevents the black-box model from overriding clear policy violations while still benefiting from ML pattern recognition.

**4. Job persistence across restarts.**
Jobs are pickled to `uploads/jobs/*.pkl` immediately after any state change. On startup, all pkl files are loaded into the in-memory `JOBS` dict, so restart recovery is automatic.

**5. Feature vector is always complete.**
The Feature Engine provides `0.0` defaults for every feature. The sklearn pipeline applies median imputation. The XGBoost model always receives a full 25-dimensional vector regardless of how sparse the uploaded documents are.

**6. Evidence graph enables auditability.**
The 5-layer DAG (Document → Segment → Feature → Finding → Decision) satisfies RBI's model explainability guidance for AI-assisted credit decisions, allowing bank credit officers to trace any model output back to the exact document page.
