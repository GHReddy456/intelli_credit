"""
Demo Data Generator — creates RISK-FLAGGED synthetic PDF documents for testing.
Company: Trident Components Pvt. Ltd.

RED FLAGS EMBEDDED:
  Annual Report : Qualified auditor opinion, receivables Rs.2.60 Cr (145 debtor days),
                  net loss, D/E 3.41, current ratio 0.82 < 1.0
  GSTR-3B       : Turnover Rs.18 Cr vs bank credits Rs.10.2 Cr (43% mismatch),
                  excess ITC claimed Rs.1.40 Cr over eligible Rs.2.80 Cr (50% excess)
  Bank Statement: Total credits Rs.10.2 Cr, 3 cheque-return entries
  ITR-6         : Income Rs.9.8 Cr (vs GST Rs.18 Cr / AR Rs.6.53 Cr - three-way mismatch)
  Legal         : Section 138 cheque-bounce, GST demand notice, supplier recovery

Expected outcome: HARD REJECT (DSCR 0.23x < minimum 1.10x)

Usage:
    python demo_data/generate_demo.py
"""

import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    HAS_RL = True
except ImportError:
    HAS_RL = False
    print("[WARN] reportlab not installed"); sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

COMPANY = "Trident Components Pvt. Ltd."
CIN     = "U29302GJ2015PTC089621"
GSTIN   = "24AACCT1234B1Z3"
PAN     = "AACCT1234B"

styles = getSampleStyleSheet()
_warn  = ParagraphStyle("W", parent=styles["Normal"], textColor=colors.red, fontSize=8)

def _doc(path):
    return SimpleDocTemplate(path, pagesize=A4, topMargin=1.8*cm, bottomMargin=1.8*cm,
                              leftMargin=2*cm, rightMargin=2*cm)

def _table(data, col_widths=None, hc="#1E3A5F"):
    col_widths = col_widths or [5*cm]*len(data[0])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), colors.HexColor(hc)),
        ("TEXTCOLOR",  (0,0),(-1,0), colors.white),
        ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0),(-1,-1), 8),
        ("GRID",       (0,0),(-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F8F9FA")]),
        ("PADDING",    (0,0),(-1,-1), 4),
    ]))
    return t

P  = lambda t,s="Normal": Paragraph(t, styles[s])
Pw = lambda t: Paragraph(t, _warn)
S  = lambda h=0.3: Spacer(1, h*cm)


def make_annual_report():
    path = os.path.join(OUT_DIR, "annual_report_abc_steel.pdf")
    doc  = _doc(path); story = []
    story += [
        P(f"<b>ANNUAL REPORT FY 2022-23</b>","Title"), S(),
        P(f"<b>Company:</b> {COMPANY}  |  CIN: {CIN}  |  GSTIN: {GSTIN}"), S(),
        P("<b>=== INDEPENDENT AUDITOR REPORT ===</b>","Heading2"), S(0.2),
        Pw("<b>QUALIFIED OPINION</b>"),
        Pw("We have audited the standalone financial statements of Trident Components Pvt. Ltd. "
           "for the year ended 31 March 2023. In our opinion, EXCEPT FOR the possible effects of "
           "the matter described in the Basis for Qualified Opinion paragraph, the financial "
           "statements give a true and fair view. This is our qualified opinion."),
        S(0.2),
        Pw("<b>Basis for Qualified Opinion:</b>"),
        Pw("Trade receivables of Rs.2.60 Crore (260 Lakhs) outstanding for more than 270 days. "
           "Management has not made provision for doubtful debts. We are unable to obtain "
           "sufficient audit evidence regarding recoverability — scope limitation applied. "
           "HAD the Company made a provision, the loss would have been higher by Rs.2.60 Crore."),
        S(0.2),
        Pw("<b>Emphasis of Matter:</b>"),
        Pw("Without qualifying our opinion: pending case under Section 138 Negotiable Instruments "
           "Act for Rs.45 Lakhs (CC No. 4521/2023, Judicial Magistrate Surat). "
           "GST demand notice for Rs.180 Lakhs excess ITC. These are emphasis of matter items."),
        S(),
        P("<b>=== BALANCE SHEET (Rs. in Lakhs) ===</b>","Heading2"), S(0.2),
    ]
    bs_data = [
        ["Item",                        "FY23",   "FY22",   "FY21"],
        ["Share Capital",               "150.00", "150.00", "150.00"],
        ["Reserves & Surplus",          "132.00", "214.00", "302.00"],
        ["Total Equity (Net Worth)",    "282.00", "364.00", "452.00"],
        ["Long-Term Borrowings",        "682.00", "620.00", "540.00"],
        ["Short-Term Borrowings",       "280.00", "240.00", "200.00"],
        ["Total Debt",                  "962.00", "860.00", "740.00"],
        ["Trade Payables",              "241.00", "198.00", "162.00"],
        ["Other Current Liabilities",   "110.00", "124.00", "125.00"],
        ["Current Liabilities",         "631.00", "562.00", "487.00"],
        ["Net Fixed Assets",            "834.00", "762.00", "680.00"],
        ["Inventories",                 "180.00", "162.00", "143.00"],
        ["Trade Receivables",           "260.00", "128.00",  "98.00"],
        ["Cash & Bank",                  "48.00",  "42.00",  "38.00"],
        ["Other Current Assets",         "32.00", "156.00", "167.00"],
        ["Current Assets",              "520.00", "488.00", "446.00"],
    ]
    story += [_table(bs_data,[6*cm,2.8*cm,2.8*cm,2.8*cm]), S()]
    story += [P("<b>=== PROFIT AND LOSS STATEMENT (Rs. in Lakhs) ===</b>","Heading2"), S(0.2)]
    pl_data = [
        ["Item",                        "FY23",   "FY22",   "FY21"],
        ["Revenue from Operations",     "653.00", "600.00", "545.00"],
        ["Other Income",                  "8.00",   "5.00",   "4.00"],
        ["Total Revenue",               "661.00", "605.00", "549.00"],
        ["Raw Material Cost",           "290.00", "265.00", "238.00"],
        ["Employee Expenses",            "88.00",  "82.00",  "74.00"],
        ["Other Operating Expenses",     "73.00",  "66.00",  "59.00"],
        ["EBITDA",                      "210.00", "192.00", "178.00"],
        ["Depreciation",                 "42.00",  "38.00",  "34.00"],
        ["EBIT",                        "168.00", "154.00", "144.00"],
        ["Interest / Finance Costs",    "250.00", "242.00", "195.00"],
        ["PBT (Loss before Tax)",       "-82.00", "-88.00", "-51.00"],
        ["Tax Expense",                   "0.00",   "0.00",   "0.00"],
        ["PAT (Net Loss)",              "-82.00", "-88.00", "-51.00"],
        ["Cash Flow from Operations",    "80.00",  "72.00",  "65.00"],
    ]
    story += [_table(pl_data,[6*cm,2.8*cm,2.8*cm,2.8*cm]), S()]
    story += [P("<b>=== KEY FINANCIAL RATIOS ===</b>","Heading2"), S(0.2)]
    ratio_data = [
        ["Ratio",               "FY23",        "FY22"],
        ["Current Ratio",       "0.82x",       "1.05x"],
        ["Debt / Equity",       "3.41x",       "2.36x"],
        ["Interest Coverage",   "0.67x",       "0.64x"],
        ["DSCR",                "0.23x",       "0.21x"],
        ["Debtor Days",         "145 days",    "78 days"],
        ["Inventory Days",      "101 days",    "99 days"],
        ["PAT Margin",          "-12.6%",      "-14.7%"],
        ["EBITDA Margin",       "32.2%",       "32.0%"],
    ]
    story += [_table(ratio_data,[6*cm,4*cm,4*cm]), S()]
    story += [
        P("<b>=== DIRECTORS REPORT ===</b>","Heading2"), S(0.2),
        P(f"Company: {COMPANY}. CIN: {CIN}. GSTIN: {GSTIN}. PAN: {PAN}."),
        P("Revenue from Operations: 653 Lakhs (FY23). Net Loss: 82 Lakhs (third consecutive year). "
          "Total Debt: 962 Lakhs. Net Worth (Total Equity): 282 Lakhs. "
          "Debt to Equity ratio (Debt/Equity): 3.41x. Current Ratio: 0.82x. "
          "Trade Receivables: 260 Lakhs. Debtor Days: 145 days (FY22: 78 days). "
          "Interest / Finance Costs: 250 Lakhs. DSCR: 0.23x. "
          "Cash Flow from Operations: 80 Lakhs. EBITDA: 210 Lakhs."),
        S(),
        P("<b>=== COLLATERAL OFFERED ===</b>","Heading2"), S(0.2),
        P("Factory premises Sachin GIDC Surat: Rs.380 Lakhs. Plant machinery: Rs.120 Lakhs. "
          "Total collateral: Rs.500 Lakhs. Loan requested: Rs.800 Lakhs. Coverage: 0.625x."),
    ]
    doc.build(story)
    print(f"[*] {path}")
    return path


def make_gstr3b():
    path = os.path.join(OUT_DIR, "gstr3b_abc_steel.pdf")
    doc  = _doc(path); story = []
    story += [
        P("<b>GSTR-3B Returns FY 2022-23</b>","Title"), S(),
        P(f"<b>GSTIN:</b> {GSTIN}  |  <b>Entity:</b> {COMPANY}  |  <b>PAN:</b> {PAN}"), S(),
    ]
    monthly = [
        ["Month","Turnover (Rs.L)","IGST","CGST","SGST","ITC Claimed (Rs.L)"],
        ["Apr-22","128.00","6.40","3.20","3.20","29.40"],
        ["May-22","140.00","7.00","3.50","3.50","32.20"],
        ["Jun-22","152.00","7.60","3.80","3.80","34.96"],
        ["Jul-22","148.00","7.40","3.70","3.70","34.04"],
        ["Aug-22","155.00","7.75","3.88","3.87","35.65"],
        ["Sep-22","160.00","8.00","4.00","4.00","36.80"],
        ["Oct-22","148.00","7.40","3.70","3.70","34.04"],
        ["Nov-22","152.00","7.60","3.80","3.80","34.96"],
        ["Dec-22","162.00","8.10","4.05","4.05","37.26"],
        ["Jan-23","168.00","8.40","4.20","4.20","38.64"],
        ["Feb-23","162.00","8.10","4.05","4.05","37.26"],
        ["Mar-23","225.00","11.25","5.63","5.62","51.75"],
        ["TOTAL","1800.00","95.00","47.51","47.49","420.96"],
    ]
    story += [_table(monthly,[2.5*cm,3*cm,2.3*cm,2.3*cm,2.3*cm,3.1*cm]), S()]
    story += [
        Pw("<b>GST SUMMARY FY 2022-23</b>"),
        Pw("Aggregate Turnover: Rs.1800 Lakhs (Rupees Eighteen Crore)"),
        Pw("Total ITC Claimed: 420 Lakhs"),
        Pw("Eligible ITC: 280 Lakhs as per GSTR-2A"),
        Pw("Excess ITC claimed over eligible: 140 Lakhs (50% excess ITC — demand issued)"),
        S(0.2),
        _table([
            ["Particulars",                          "Amount (Rs. Lakhs)"],
            ["ITC Claimed in GSTR-3B filings",       "420"],
            ["ITC available as per GSTR-2A eligible","280"],
            ["Excess ITC Claimed",                   "140"],
            ["GST Demand Notice (ITC reversal + penalty)","180"],
        ],[9*cm,5*cm]),
        S(0.2),
        Pw("Demand Notice No. GST/DEMAND/2023/1142 dated 15-Dec-2023 issued for excess "
           "ITC of Rs.140 Lakhs plus interest Rs.28 Lakhs plus penalty Rs.12 Lakhs = Rs.180 Lakhs. "
           "Show Cause Notice served. Regulatory violation confirmed. Appeal filed."),
    ]
    doc.build(story)
    print(f"[*] {path}")
    return path


def make_bank_statement():
    path = os.path.join(OUT_DIR, "bank_statement_abc_steel.pdf")
    doc  = _doc(path); story = []
    story += [
        P("<b>Bank Account Statement FY 2022-23</b>","Title"), S(),
        P(f"Account Holder: {COMPANY}  |  Account No: 98765432101  |  IFSC: HDFC0002345"), S(),
        P("Period: 01-Apr-2022 to 31-Mar-2023"), S(),
    ]
    txn = [
        ["Date","Particulars","Debit (Rs.L)","Credit (Rs.L)","Balance (Rs.L)"],
        ["01-Apr-22","Opening Balance","-","-","48.20"],
        ["05-Apr-22","NEFT Cr - Sunrise Trading","-","72.00","120.20"],
        ["10-Apr-22","RTGS Dr - JSW Steel RM Payment","48.00","-","72.20"],
        ["15-Apr-22","NEFT Cr - Metro Industrial","-","68.00","140.20"],
        ["20-Apr-22","HDFC EMI - Term Loan","38.00","-","102.20"],
        ["22-Apr-22","CHEQUE RETURN Insuff Funds Chq004521 Rs45L - Section 138 NI Act","45.00","-","57.20"],
        ["25-Apr-22","SALARY NEFT Transfer","22.00","-","35.20"],
        ["30-Apr-22","NEFT Cr - Apex Fabricators","-","58.00","93.20"],
        ["05-May-22","RTGS Cr - National Metal Works","-","82.00","175.20"],
        ["12-May-22","RTGS Dr - SAIL RM Purchase","62.00","-","113.20"],
        ["18-May-22","EMI - Working Capital Loan","28.00","-","85.20"],
        ["25-May-22","NEFT Cr - Bharat Steel Corp","-","78.00","163.20"],
        ["10-Jun-22","CHEQUE RETURN Stop Payment Chq005123 Rs28L","28.00","-","117.20"],
        ["15-Jun-22","NEFT Cr - Prism Metal","-","92.00","209.20"],
        ["30-Jun-22","Salary + expenses","30.00","-","179.20"],
        ["15-Jul-22","NEFT Cr - Shree Traders","-","88.00","267.20"],
        ["22-Jul-22","EMI Term Loan","38.00","-","229.20"],
        ["31-Jul-22","CHEQUE RETURN Drawer Account Frozen Chq006841 Rs32L","32.00","-","197.20"],
        ["10-Aug-22","NEFT Cr - Indus Components","-","95.00","292.20"],
        ["20-Aug-22","RTGS Dr - Supplier advance","55.00","-","237.20"],
        ["15-Sep-22","NEFT Cr - Kumar Enterprises","-","82.00","301.20"],
        ["30-Sep-22","EMI + insurance","32.00","-","269.20"],
        ["15-Oct-22","NEFT Cr - Skyline Fabricators","-","79.00","348.20"],
        ["30-Oct-22","EMI + Salary","62.00","-","286.20"],
        ["15-Nov-22","NEFT Cr - Ferro Alloys Ltd","-","88.00","374.20"],
        ["28-Nov-22","RTGS Dr - Supplier advance","45.00","-","329.20"],
        ["15-Dec-22","NEFT Cr - National Alloys","-","91.00","420.20"],
        ["28-Dec-22","EMI + Salary","62.00","-","358.20"],
        ["15-Jan-23","NEFT Cr - Sunrise Metal","-","86.00","444.20"],
        ["25-Jan-23","RTGS Dr - JSW payment","52.00","-","392.20"],
        ["15-Feb-23","NEFT Cr - Bharat Components","-","78.00","470.20"],
        ["25-Feb-23","EMI + GST payment","58.00","-","412.20"],
        ["15-Mar-23","NEFT Cr - Apex Trading","-","82.00","494.20"],
        ["25-Mar-23","RTGS Dr - Bulk RM purchase","68.00","-","426.20"],
        ["31-Mar-23","Salary Mar + office expenses","30.00","-","396.20"],
    ]
    story += [_table(txn,[2.2*cm,7.2*cm,2*cm,2*cm,2.4*cm]), S()]
    story += [
        P("<b>ACCOUNT SUMMARY:</b>"),
        P("Opening Balance (01-Apr-22): 48.20 Lakhs"),
        P("Closing Balance (31-Mar-23): 396.20 Lakhs"),
        Pw("Total Credits: 1020 Lakhs for FY 2022-23 (Rupees Ten Crore Twenty Lakhs)"),
        Pw("Total Debits: 672.00 Lakhs"),
        Pw("<b>CHEQUE RETURNS NOTED — 3 instances (cheque dishonour events):</b>"),
        Pw("1. Chq#004521 dated 22-Apr-22 Rs.45 Lakhs — Insufficient Funds (Section 138 NI Act)"),
        Pw("2. Chq#005123 dated 10-Jun-22 Rs.28 Lakhs — Stop Payment instruction"),
        Pw("3. Chq#006841 dated 31-Jul-22 Rs.32 Lakhs — Account Frozen"),
        S(0.2),
        Pw("<b>CRITICAL OBSERVATION:</b> Total Bank Credits Rs.1020 Lakhs (Rs.10.20 Crore) "
           "is significantly lower than GSTR-3B declared turnover of Rs.1800 Lakhs (Rs.18 Crore). "
           "Unexplained difference of Rs.780 Lakhs (43%) — possible revenue inflation in GST."),
        P("Account No: 98765432101. IFSC: HDFC0002345."),
    ]
    doc.build(story)
    print(f"[*] {path}")
    return path


def make_itr():
    path = os.path.join(OUT_DIR, "itr_abc_steel.pdf")
    doc  = _doc(path); story = []
    story += [
        P("<b>Income Tax Return ITR-6  AY 2023-24 (FY 2022-23)</b>","Title"), S(),
        P(f"<b>Company:</b> {COMPANY}  |  <b>PAN:</b> {PAN}  |  <b>CIN:</b> {CIN}"), S(),
        P("Assessment Year: 2023-24  |  Return Type: Original  |  Filing Date: 28-Oct-2023"), S(),
    ]
    itr_data = [
        ["Schedule / Item",                    "Amount (Rs. Lakhs)"],
        ["Gross Receipts / Business Turnover",  "980.00"],
        ["Less: Cost of Goods Sold",            "436.00"],
        ["Gross Profit",                        "544.00"],
        ["Less: Operating Expenses",            "334.00"],
        ["Net Profit before Depreciation",      "210.00"],
        ["Less: Depreciation (Schedule WDV)",    "42.00"],
        ["Net Profit after Depreciation",       "168.00"],
        ["Less: Interest and Finance Charges",  "250.00"],
        ["Profit (Loss) before Tax",            "-82.00"],
        ["Tax on above",                          "0.00"],
        ["Net Profit (Loss) after Tax",         "-82.00"],
        ["Gross Total Income",                  "980.00"],
        ["Deductions under Chapter VI-A",         "0.00"],
        ["Total Taxable Income",                "980.00"],
        ["Tax Payable",                           "0.00"],
        ["Advance Tax Paid",                      "0.00"],
        ["TDS Credited",                         "12.80"],
        ["Refund Due",                           "12.80"],
    ]
    story += [_table(itr_data,[10*cm,4.5*cm]), S()]
    story += [
        Pw("<b>KEY ITR FIGURES:</b>"),
        Pw("Gross Total Income: 980 Lakhs (Rs.9.80 Crore) as declared in ITR-6."),
        Pw("This gross total income of 980 Lakhs differs from Annual Report Revenue of 653 Lakhs."),
        Pw("GSTR-3B Aggregate Turnover is Rs.1800 Lakhs — all three figures are inconsistent."),
        Pw("Net Loss of Rs.82 Lakhs reported for third consecutive year."),
        Pw("PAN: AACCT1234B. Return filed u/s 139(1). Income from business/profession: 980 Lakhs."),
    ]
    doc.build(story)
    print(f"[*] {path}")
    return path


def make_legal():
    path = os.path.join(OUT_DIR, "legal_docs_abc_steel.pdf")
    doc  = _doc(path); story = []
    story += [
        P("<b>LEGAL PROCEEDINGS COMPILATION</b>","Title"), S(),
        P(f"<b>Company:</b> {COMPANY}  |  CIN: {CIN}"), S(),
    ]
    story += [
        Pw("<b>CASE 1 — CHEQUE BOUNCE (Section 138 NI Act)</b>"),
        Pw("Case No. CC 4521/2023. Court: Judicial Magistrate First Class Surat. "
           "Plaintiff: Sigma Metal Suppliers Pvt Ltd. Defendant: Trident Components Pvt Ltd. "
           "Amount in dispute: Rs.45 Lakhs. Nature: Cheque dishonour insufficient funds. "
           "Criminal complaint filed under Section 138 Negotiable Instruments Act 1881. "
           "Recovery suit pending. Next hearing 15-Mar-2024. Severity: MEDIUM."),
        S(),
        Pw("<b>CASE 2 — GST DEMAND NOTICE APPEAL (HIGH severity)</b>"),
        Pw("Case No. Appeal 1234/2023. Forum: GST Appellate Authority Gujarat. "
           "Petitioner: Trident Components Pvt Ltd. Respondent: CGST Commissionerate Surat. "
           "Amount in dispute: Rs.180 Lakhs (ITC reversal demand plus interest plus penalty). "
           "Nature: Demand for excess Input Tax Credit claimed vs GSTR-2A eligible. "
           "Show Cause Notice followed by demand order. Appeal admitted by tribunal. "
           "Next date: 22-Apr-2024. Regulatory violation. Severity: HIGH."),
        S(),
        Pw("<b>CASE 3 — SUPPLIER RECOVERY CIVIL SUIT</b>"),
        Pw("Case No. Civil Suit 892/2022. Court: City Civil Court Surat. "
           "Plaintiff: Ferro Alloys Corporation Ltd. Defendant: Trident Components Pvt Ltd. "
           "Amount in dispute: Rs.62 Lakhs unpaid trade dues. Recovery suit for outstanding "
           "receivables. Summons served. Evidence stage. Next hearing: 08-Feb-2024. "
           "Severity: MEDIUM. Cheque bounce related."),
        S(),
        _table([
            ["Case","Forum","Amount (Rs.L)","Severity"],
            ["CC-4521/23 Sec 138","Magistrate Surat","45","MEDIUM"],
            ["Appeal-1234/23 GST","GST Appellate Gujarat","180","HIGH"],
            ["CS-892/22 Recovery","Civil Court Surat","62","MEDIUM"],
            ["TOTAL","","287","HIGH"],
        ],[4*cm,5*cm,2.8*cm,2.8*cm]),
        S(),
        Pw("Total litigation exposure: Rs.287 Lakhs including HIGH severity GST appeal. "
           "Cheque dishonour under Section 138 NI Act indicates liquidity stress. "
           "Writ of recovery and criminal prosecution pending against the company."),
    ]
    doc.build(story)
    print(f"[*] {path}")
    return path


if __name__ == "__main__":
    print("="*60)
    print(f"Generating RED-FLAG demo documents for: {COMPANY}")
    print("="*60)
    make_annual_report()
    make_gstr3b()
    make_bank_statement()
    make_itr()
    make_legal()
    print()
    print("[OK] All demo documents created in demo_data/")
    print()
    print("Expected appraisal outcome: HARD REJECT")
    print("  DSCR: 0.23x (min 1.10x) -- HARD REJECT TRIGGER")
    print("  D/E:  3.41x  |  Current Ratio: 0.82x (below 1.0)")
    print("  PAT: -Rs.82L (Net Loss, 3rd consecutive year)")
    print("  GST vs Bank mismatch: 1800L vs 1020L = 43% (HIGH)")
    print("  ITC excess: 420L vs 280L = 50% (HIGH)")
    print("  ITR vs AR mismatch: 980L vs 653L = 33% (HIGH)")
    print("  3 active litigation cases inc Section 138 + GST demand")
