"""
Full Agent Stress Test - measures real-time performance of every agent.
Run: python stress_test.py
"""
import sys, time, json
sys.path.insert(0, '.')

COMPANY  = "ABG Shipyard"            # known NPA + CBI fraud case  ← real stress test
PROMOTER = ["Rishi Agarwal"]
COMPANY2 = "Tata Steel"              # healthy company ← should score well
SEP = "=" * 62

timings = {}

def hdr(n, title):
    print(f"\n{SEP}\n[{n}/7] {title}\n{SEP}")

def tick(label, t0):
    elapsed = round(time.time() - t0, 2)
    timings[label] = elapsed
    print(f"  >>> Completed in {elapsed}s")
    return elapsed


# ── 1. NewsScraper ─────────────────────────────────────────────────────────────
hdr(1, "NewsScraper  (5 parallel DDG queries)")
t0 = time.time()
from research.news_scraper import NewsScraper
news = NewsScraper().scrape(COMPANY, PROMOTER)
tick("NewsScraper", t0)
print(f"  Total articles    : {news['total_articles']}")
print(f"  Negative          : {news['negative_count']}")
print(f"  Positive          : {news['positive_count']}")
print(f"  Litigation signals: {len(news['litigation_news'])}")
print(f"  Sentiment score   : {news['news_sentiment_score']}  (0=good, 1=bad)")
for a in news['articles'][:3]:
    print(f"    [{a['sentiment']:8s}] {a['title'][:72]}")
PASS1 = news['negative_count'] > 0
print(f"  VERDICT: {'PASS ✓ — negative coverage detected' if PASS1 else 'WARN — no negative articles found'}")


# ── 2. LitigationDetector ──────────────────────────────────────────────────────
hdr(2, "LitigationDetector  (5 parallel DDG queries)")
t0 = time.time()
from research.litigation_detector import LitigationDetector
lit = LitigationDetector().detect(COMPANY, [])
tick("LitigationDetector", t0)
print(f"  Litigation count  : {lit['litigation_count']}")
print(f"  High severity     : {lit['high_severity_count']}")
print(f"  Severity score    : {lit['litigation_severity_score']}  (0=clean, 1=critical)")
for c in lit['cases'][:3]:
    print(f"    [{c['severity']:8s}] {c['summary'][:72]}")
PASS2 = lit['litigation_count'] > 0
print(f"  VERDICT: {'PASS ✓ — litigation found' if PASS2 else 'WARN — no cases returned'}")


# ── 3. SectorAnalyzer ──────────────────────────────────────────────────────────
hdr(3, "SectorAnalyzer  (3 parallel DDG regulatory queries)")
t0 = time.time()
from research.sector_analyzer import SectorAnalyzer
sector = SectorAnalyzer().analyze(COMPANY, [])
tick("SectorAnalyzer", t0)
print(f"  Sector detected   : {sector['sector']}")
print(f"  Risk score        : {sector['sector_risk_score']}")
print(f"  Outlook           : {sector['sector_outlook']}")
print(f"  Regulatory hits   : {sector['regulatory_violation_count']}")
print(f"  Headwinds         : {sector.get('headwinds',[])[0][:60] if sector.get('headwinds') else 'none'}")
print(f"  Summary           : {sector.get('conditions_summary','')[:80]}")
PASS3 = sector['sector_risk_score'] > 0
print(f"  VERDICT: {'PASS ✓' if PASS3 else 'FAIL'}")


# ── 4. FraudDetectionAgent (Benford + mock bank txns) ─────────────────────────
hdr(4, "FraudDetectionAgent  (Benford Law + circular trading)")
t0 = time.time()
from agents.fraud_detection_agent import FraudDetectionAgent

# Bank table with proper headers so TransactionGraph._extract_transactions can parse them.
# Round-trip pattern (ENTITY_A pays and receives back) triggers circular trading detection.
# Leading-digit 9 anomaly in VENDOR rows triggers Benford Law flag.
bank_table = {
    "headers": ["Date", "Narration", "Debit", "Credit", "Balance"],
    "rows": [
        {"Date": "2024-01-01", "Narration": "NEFT/ENTITY-A/Payment",  "Debit": "10000000", "Credit": "",        "Balance": "15000000"},
        {"Date": "2024-01-03", "Narration": "NEFT/ENTITY-A/Receipt",  "Debit": "",         "Credit": "9500000","Balance": "6000000"},
        {"Date": "2024-01-05", "Narration": "RTGS/ENTITY-B/Transfer", "Debit": "10000000", "Credit": "",        "Balance": "2000000"},
        {"Date": "2024-01-07", "Narration": "RTGS/ENTITY-B/Return",   "Debit": "",         "Credit": "9800000","Balance": "8000000"},
        {"Date": "2024-01-10", "Narration": "NEFT/ENTITY-C/Forward",  "Debit": "15000000", "Credit": "",        "Balance": "3000000"},
        {"Date": "2024-01-12", "Narration": "NEFT/ENTITY-C/Return",   "Debit": "",         "Credit":"14800000","Balance": "4000000"},
        {"Date": "2024-01-15", "Narration": "NEFT/ENTITY-A/Payment",  "Debit": "10000000", "Credit": "",        "Balance": "2500000"},
        {"Date": "2024-01-17", "Narration": "NEFT/ENTITY-A/Receipt",  "Debit": "",         "Credit": "9600000","Balance": "5000000"},
        # Benford leading-9 anomaly
        {"Date": "2024-01-20", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9000000",  "Credit": "",        "Balance": "1000000"},
        {"Date": "2024-01-22", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9100000",  "Credit": "",        "Balance": "900000"},
        {"Date": "2024-01-24", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9200000",  "Credit": "",        "Balance": "800000"},
        {"Date": "2024-01-26", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9300000",  "Credit": "",        "Balance": "700000"},
        {"Date": "2024-01-28", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9400000",  "Credit": "",        "Balance": "600000"},
        {"Date": "2024-01-30", "Narration": "RTGS/VENDOR/Purchase",   "Debit": "9500000",  "Credit": "",        "Balance": "500000"},
    ],
}

class FakeDoc:
    doc_type = "bank_statement"
    text_content = ""

fraud = FraudDetectionAgent().run([FakeDoc()], [bank_table], {})
tick("FraudDetectionAgent", t0)
print(f"  Fraud risk score  : {fraud.get('fraud_risk_score', 0)}/100")
print(f"  Circular trading  : {fraud.get('circular_trading_score', 0)}")
print(f"  Benford deviation : {fraud.get('benford_deviation_score', 0)}")
print(f"  Flags             : {len(fraud.get('all_flags', []))}")
print(f"  Hard reject?      : {fraud.get('is_hard_reject', False)}")
for f in fraud.get('all_flags', [])[:3]:
    print(f"    - {f.get('flag','?')}: {str(f.get('detail',''))[:60]}")
PASS4 = fraud.get('fraud_risk_score', 0) > 0
print(f"  VERDICT: {'PASS ✓' if PASS4 else 'WARN — score stayed at 0'}")


# ── 5. PromoterIntelligenceAgent ───────────────────────────────────────────────
hdr(5, "PromoterIntelligenceAgent  (graph construction)")
t0 = time.time()
from agents.promoter_intelligence_agent import PromoterIntelligenceAgent

# Mock legal doc with director names
class FakeLegalDoc:
    doc_type = "legal"
    file_name = "MOA.pdf"
    text_content = """
    MEMORANDUM OF ASSOCIATION
    Directors: Rishi Agarwal (DIN: 00012345), Santosh Kabra (DIN: 00067890)
    Promoter shareholding: Rishi Agarwal 42%, Santosh Kabra 18%
    Previous company: ABG International Pvt Ltd, Rishi Agarwal — Director
    Charge: Rs 2800 Crore outstanding with SBI, PNB, IDBI
    NCLT Case No. C/21/2022 — Corporate Insolvency Resolution Process initiated
    """

# PromoterIntelligenceAgent.run() reads research["promoter_names"], research["mca"], and research["litigation"]
promoter_research = {
    "promoter_names": ["Rishi Agarwal", "Santosh Kabra"],
    "mca": {
        "director_list":       [{"name": "Rishi Agarwal"}, {"name": "Santosh Kabra"}],
        "director_count":      2,
        "company_charges":     [{"lender": "SBI"}, {"lender": "PNB"}, {"lender": "IDBI"}],
        "disqualification_flag": True,
    },
    "litigation": {
        "cases": [
            {"summary": "NCLT CIRP ABG Shipyard CP/21/2022", "severity": "CRITICAL"},
            {"summary": "ED PMLA Attachment Order",          "severity": "CRITICAL"},
            {"summary": "CBI FIR Rs 22842 Crore fraud",      "severity": "CRITICAL"},
            {"summary": "DRT Recovery Application SBI",      "severity": "HIGH"},
        ],
        "litigation_severity_score": 1.0,
        "high_severity_count": 4,
    },
}
promoter = PromoterIntelligenceAgent().run([FakeLegalDoc()], promoter_research)
tick("PromoterIntelligenceAgent", t0)
print(f"  Network risk      : {promoter.get('promoter_network_risk', 0)}")
print(f"  Promoter count    : {promoter.get('promoter_count', 0)}")
print(f"  Director count    : {promoter.get('director_count', 0)}")
print(f"  Litigation links  : {promoter.get('litigation_links', 0)}")
print(f"  Graph nodes       : {promoter.get('graph_nodes', 0)}")   # int (G.number_of_nodes())
PASS5 = promoter.get('promoter_count', 0) > 0 or promoter.get('promoter_network_risk', 0) > 0
print(f"  VERDICT: {'PASS ✓' if PASS5 else 'WARN — no promoters detected'}")


# ── 6. DocumentIntelligenceAgent ───────────────────────────────────────────────
hdr(6, "DocumentIntelligenceAgent  (regex pattern audit scan)")
t0 = time.time()
from agents.document_intelligence_agent import DocumentIntelligenceAgent

class FakeSection:
    def __init__(self, label, raw_text):
        self.label    = label
        self.raw_text = raw_text

class FakeAnnualReport:
    doc_type = "annual_report"
    file_name = "annual_report.pdf"
    text_content = ""
    sections = [
        FakeSection("AUDITOR_REPORT", (
            "Going Concern: There exists a material uncertainty regarding the company's ability "
            "to continue as a going concern due to accumulated losses of Rs 1450 Crore. "
            "Qualified Opinion: The financial statements do not give a true and fair view. "
            "Material weakness identified in internal financial controls. "
            "Change of auditor — resigned as auditor due to scope limitation."
        )),
        FakeSection("DIRECTORS_REPORT", (
            "Revenue declined from Rs 3200 Cr to Rs 1100 Cr. "
            "Related party transactions amount to Rs 890 Crore (81% of revenue). "
            "Promoter holding pledged: 91% of promoter shares pledged with lenders. "
            "Show cause notice issued by SEBI for non-disclosure. "
            "Resignation of director Mr Santosh Kabra on 12/03/2024."
        )),
        FakeSection("NOTES_ACCOUNTS", (
            "AGM was not held for FY 2022-23. "
            "Contingent liabilities: Rs 1800 Crore outstanding litigation. "
            "Management override of controls suspected by internal audit committee."
        )),
    ]
    segment_summary = {
        "sections_found": ["AUDITOR_REPORT", "DIRECTORS_REPORT", "NOTES_ACCOUNTS"],
        "key_financial_figures": {"revenue": 1100, "net_loss": 1450},
    }

doc_agent = DocumentIntelligenceAgent().run([FakeAnnualReport()])
tick("DocumentIntelligenceAgent", t0)
print(f"  Audit flags       : {len(doc_agent.get('audit_flags', []))}")
print(f"  Governance flags  : {len(doc_agent.get('governance_flags', []))}")
print(f"  High severity     : {doc_agent.get('high_severity_count', 0)}")
print(f"  Overall doc risk  : {doc_agent.get('overall_doc_risk', 0)}")
for f in doc_agent.get('audit_flags', [])[:3]:
    print(f"    AUDIT : {str(f)[:70]}")
for f in doc_agent.get('governance_flags', [])[:3]:
    print(f"    GOV   : {str(f)[:70]}")
PASS6 = len(doc_agent.get('audit_flags', [])) > 0
print(f"  VERDICT: {'PASS ✓ — audit flags detected' if PASS6 else 'FAIL — no flags found'}")


# ── 7. FinancialConsistencyEngine ──────────────────────────────────────────────
hdr(7, "FinancialConsistencyEngine  (GST/ITR/Bank cross-check)")
t0 = time.time()
from verification.financial_consistency_engine import FinancialConsistencyEngine

class FakeGSTDoc:
    doc_type = "gst"
    # Must contain: "total taxable value" (GSTBankValidator), "itc claimed" (GSTR2A checker),
    # "aggregate turnover" (GSTR2A turnover extractor)
    text_content = (
        "GSTR-3B Return  Aggregate Turnover: 85000  "
        "Total Taxable Value: 85000  "
        "ITC Claimed (3B): 6200"
    )

class FakeBankDoc:
    doc_type = "bank_statement"
    # "total credits" is the keyword the bank validator regex matches on
    text_content = "Total Credits: 31000  Total Debits: 29800"  # GST=85000 vs Bank=31000 → 174% mismatch

class FakeITRDoc:
    doc_type = "itr"
    # Must contain "gross total income" or "total income" (ITR income extractor)
    text_content = "Schedule BP  Gross Total Income: 49000  Net Profit: 1200"  # GST=85000 vs ITR=49000 → 42% mismatch  # 850→490: hidden income

class FakeGSTR2A:
    # GSTR2A checker reads doc_type == "gst" only, so keep it as "gst"
    doc_type = "gst"
    # Must contain "eligible itc" or "itc available" (for GSTR2A ITC available extractor)
    text_content = "GSTR-2A  Eligible ITC Available: 3800"  # claimed 6200 vs eligible 3800 → fake ITC

# Annual report doc for ITR cross-check (revenue from operations)
class FakeARDoc:
    doc_type = "annual_report"
    file_name = "annual_report_financial.pdf"
    text_content = "Revenue from Operations: 110000  Net Revenue: 110000"  # AR=110000 vs ITR=49000 → mismatch
    sections = []
    segment_summary = {"sections_found": [], "key_financial_figures": {}}

verification = FinancialConsistencyEngine().run(
    [FakeGSTDoc(), FakeBankDoc(), FakeITRDoc(), FakeGSTR2A(), FakeARDoc()], []
)
tick("FinancialConsistencyEngine", t0)
ms = verification.get("mismatch_scores", {})
print(f"  GST-Bank mismatch : {ms.get('gst_bank_mismatch_score', 0):.3f}  (>0.15 = flag)")
print(f"  GSTR2A-3B mismatch: {ms.get('gstr2a_3b_mismatch_score', 0):.3f}  (>0.10 = flag)")
print(f"  ITR-Revenue mismtch: {ms.get('itr_revenue_mismatch_score', 0):.3f}  (>0.20 = flag)")
print(f"  Flags             : {len(verification.get('flags', []))}")
for f in verification.get('flags', [])[:3]:
    print(f"    - {str(f)[:70]}")
PASS7 = any(v > 0 for v in ms.values())
print(f"  VERDICT: {'PASS ✓ — mismatches detected' if PASS7 else 'WARN — no mismatches computed'}")


# ── SUMMARY ────────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STRESS TEST SUMMARY")
print(SEP)
passes = [PASS1, PASS2, PASS3, PASS4, PASS5, PASS6, PASS7]
labels = ["NewsScraper", "LitigationDetector", "SectorAnalyzer",
          "FraudDetectionAgent", "PromoterIntelligenceAgent",
          "DocumentIntelligenceAgent", "FinancialConsistencyEngine"]
for label, t, p in zip(labels, timings.values(), passes):
    status = "PASS ✓" if p else "WARN ⚠"
    print(f"  {status}  {label:<30s}  {t:5.1f}s")

total = sum(timings.values())
print(f"\n  Total wall time (sequential): {total:.1f}s")
print(f"  Pipeline runs agents in parallel → actual time ~{max(timings.values()):.0f}–{total//2:.0f}s")
print(f"\n  Passed: {sum(passes)}/7   Warned: {7-sum(passes)}/7")
print(SEP)
