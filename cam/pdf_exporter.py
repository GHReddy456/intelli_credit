"""
PDF Exporter -- renders the CAM dict to a professional PDF using ReportLab.
Section order: Executive Summary -> Borrower Profile -> Facility Structure ->
  Five Cs -> Financial Ratios -> Fraud & Integrity -> Promoter & Governance ->
  Sector Outlook -> AI Risk Attribution (SHAP) -> Evidence Traceability ->
  Sanction Recommendation.
"""
from __future__ import annotations
import io, os
from typing import Dict, Any
from loguru import logger

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

GREEN  = colors.HexColor("#059669")
AMBER  = colors.HexColor("#D97706")
RED    = colors.HexColor("#DC2626")
NAVY   = colors.HexColor("#1E3A5F")
TEAL   = colors.HexColor("#0F766E")
LIGHT  = colors.HexColor("#F3F4F6")
WHITE  = colors.white
BLACK  = colors.black


def _sc(v) -> str:
    """Safe-cell: coerce any value to a plain string safe for ReportLab Table cells.
    Lists/tuples are joined; None becomes 'N/A'."""
    if v is None:
        return "N/A"
    if isinstance(v, (list, tuple)):
        return ", ".join(str(i) for i in v) if v else "N/A"
    return str(v)


def _verdict_color(verdict: str):
    if verdict == "APPROVE":             return GREEN
    if verdict == "CONDITIONAL_APPROVE": return AMBER
    return RED


def _shap_waterfall_image(shap_result: Dict) -> bytes | None:
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        drivers = shap_result.get("top_drivers", [])[:10]
        if not drivers:
            return None
        names  = [d["feature"].replace("_", " ").title() for d in drivers]
        values = [d["shap_value"] for d in drivers]
        bar_colors = ["#DC2626" if v > 0 else "#059669" for v in values]
        fig, ax = plt.subplots(figsize=(9, 4))
        y_pos = np.arange(len(names))
        ax.barh(y_pos, values, color=bar_colors, edgecolor="none", height=0.55)
        ax.set_yticks(y_pos); ax.set_yticklabels(names, fontsize=8)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("SHAP Value  (positive = increases default risk, negative = reduces risk)", fontsize=8)
        ax.set_title("Top Risk Drivers -- SHAP Attribution", fontsize=10, fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format="png", dpi=150); plt.close(fig)
        buf.seek(0); return buf.read()
    except Exception as e:
        logger.warning(f"[PDF] SHAP chart skipped: {e}")
        return None


class PDFExporter:

    def export(self, cam: Dict[str, Any], shap_result: Dict, output_path: str) -> str:
        logger.info(f"[PDF] Generating CAM PDF -> {output_path}")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title",  fontSize=15, textColor=NAVY,   spaceAfter=4,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)
        h1_style    = ParagraphStyle("h1",     fontSize=11, textColor=NAVY,   spaceAfter=3,
                                     fontName="Helvetica-Bold", spaceBefore=6)
        h2_style    = ParagraphStyle("h2",     fontSize=9.5, textColor=TEAL,  spaceAfter=2,
                                     fontName="Helvetica-Bold")
        body_style  = ParagraphStyle("body",   fontSize=9,   spaceAfter=2,     fontName="Helvetica")
        small_style = ParagraphStyle("small",  fontSize=7.5,spaceAfter=2,     fontName="Helvetica",
                                     textColor=colors.grey)
        mono_style  = ParagraphStyle("mono",   fontSize=8,  spaceAfter=2,     fontName="Courier",
                                     textColor=colors.darkblue)
        pre_style   = ParagraphStyle("pre",    fontSize=8.5,spaceAfter=2,     fontName="Helvetica",
                                     leading=12, textColor=BLACK)

        story = []

        meta     = cam["meta"]
        dec      = cam["decision_block"]
        verdict  = dec["verdict"]
        v_color  = _verdict_color(verdict)
        verdict_display = verdict.replace("_", " ")

        # ── Cover / Letterhead ────────────────────────────────────────────────
        story.append(Paragraph("CREDIT APPRAISAL MEMORANDUM", title_style))
        story.append(Paragraph("Intelli-Credit AI Engine  |  Confidential", small_style))
        story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
        story.append(Spacer(1, 0.3*cm))

        meta_data = [
            ["Borrower",    meta["company_name"],        "Date",          meta["date"]],
            ["Loan Purpose", meta["loan_purpose"],       "Prepared by",   meta["prepared_by"]],
            ["Amount (Cr)", str(meta["amount_crore"]),   "CAM Version",   meta["version"]],
        ]
        mt = Table(meta_data, colWidths=[3*cm, 7.5*cm, 3*cm, 4*cm])
        mt.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",   (2,0), (2,-1), "Helvetica-Bold"),
            ("BACKGROUND", (0,0), (-1,-1), LIGHT),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(mt); story.append(Spacer(1, 0.4*cm))

        # ── Decision Banner ───────────────────────────────────────────────────
        score    = dec["credit_score"]
        grade    = dec["risk_grade"]
        pd_val   = dec["probability_default"]
        ci_low   = dec.get("score_ci_low", "N/A")
        ci_high  = dec.get("score_ci_high", "N/A")
        loan_d   = dec.get("loan_details", {})
        loan_line = ""
        if loan_d:
            loan_line = (
                f"Recommended Facility: Rs.{loan_d.get('max_loan_crore','N/A')} Cr  |  "
                f"Rate: {loan_d.get('interest_rate_pct','N/A')}% p.a.  |  "
                f"Tenor: {loan_d.get('tenure_years','N/A')} years"
            )

        vp = ParagraphStyle("vd", fontSize=14, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER)
        sp = ParagraphStyle("ds", fontSize=9,  textColor=WHITE, alignment=TA_CENTER)
        lp = ParagraphStyle("ll", fontSize=8,  textColor=WHITE, alignment=TA_CENTER)
        banner_data = [
            [Paragraph(f"<b>{verdict_display}</b>", vp)],
            [Paragraph(f"Credit Score: {score:.1f}/100  [CI: {ci_low}-{ci_high}]  |  Risk Grade: {grade}  |  PD: {pd_val:.1%}", sp)],
            [Paragraph(loan_line, lp)],
        ]
        bt = Table(banner_data, colWidths=[17*cm])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), v_color),
            ("PADDING",    (0,0), (-1,-1), 8),
        ]))
        story.append(bt); story.append(Spacer(1, 0.4*cm))

        # ═══════════════════════════════════════════════════════════════════════
        # Section 1 -- Executive Summary
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("1. Executive Summary", h1_style))
        exec_text = _sc(cam.get("executive_summary", ""))
        for line in exec_text.split("\n"):
            ln = line.strip()
            if not ln:
                story.append(Spacer(1, 0.1*cm))
            elif ln.endswith("SUMMARY") or ln.endswith("APPROVAL") or ln.endswith("REJECTION"):
                story.append(Paragraph(f"<b>{ln}</b>", body_style))
            else:
                story.append(Paragraph(ln, body_style))
        story.append(Spacer(1, 0.3*cm))

        # Conditions precedent
        conds = dec.get("conditions", [])
        if conds:
            story.append(Paragraph("Conditions Precedent / Subsequent", h2_style))
            for i, c in enumerate(conds, 1):
                story.append(Paragraph(f"{i}. {c}", body_style))
            story.append(Spacer(1, 0.2*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 2 -- Borrower Profile
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("2. Borrower Profile", h1_style))
        bp = cam.get("borrower_profile", {})
        bp_rows = [
            ["Company Name",         _sc(bp.get("company_name")),    "Sector",     _sc(bp.get("sector"))],
            ["GSTIN",                _sc(bp.get("gstin")),            "PAN",        _sc(bp.get("pan"))],
            ["CIN / Registration",   _sc(bp.get("cin")),              "FY Assessed",_sc(bp.get("financial_year_assessed"))],
            ["Est. Turnover (Cr)",   _sc(bp.get("estimated_turnover_cr")), "Documents", ", ".join(str(x) for x in bp.get("doc_types_submitted",[]))],
            ["Registered Address",   _sc(bp.get("registered_address")), "", ""],
        ]
        bpt = Table(bp_rows, colWidths=[4*cm, 6*cm, 3*cm, 4.5*cm])
        bpt.setStyle(TableStyle([
            ("FONTSIZE",  (0,0), (-1,-1), 8),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
            ("BACKGROUND",(0,0), (-1,-1), LIGHT),
            ("GRID",      (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",   (0,0), (-1,-1), 4),
            ("SPAN",      (1,4), (3,4)),
        ]))
        story.append(bpt); story.append(Spacer(1, 0.4*cm))

        # ═══════════════════════════════════════════════════════════════════════
        # Section 3 -- Facility Structure
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("3. Proposed Facility Structure", h1_style))
        fs = cam.get("facility_structure", {})
        sec = fs.get("security", {})
        fs_rows = [
            ["Total Facility",         f"Rs. {_sc(fs.get('total_facility_cr'))} Cr"],
            ["Working Capital Limit",  f"Rs. {_sc(fs.get('working_capital_cr'))} Cr  (revolving, annual review)"],
            ["Term Loan",              f"Rs. {_sc(fs.get('term_loan_cr'))} Cr"],
            ["Interest Rate",          f"{_sc(fs.get('interest_rate_pct'))}% p.a.  (Base {_sc(fs.get('base_rate_pct'))}% + Risk Premium {_sc(fs.get('risk_premium_pct'))}%)"],
            ["Tenor",                  f"{_sc(fs.get('tenure_years'))} years"],
            ["Approx. Monthly EMI",    f"Rs. {_sc(fs.get('approx_monthly_emi_cr'))} Cr (term loan portion)"],
            ["Primary Security",       _sc(sec.get("primary"))],
            ["Collateral Security",    _sc(sec.get("collateral"))],
            ["Personal Guarantee",     _sc(sec.get("guarantee"))],
            ["Repayment",              _sc(fs.get("repayment_terms"))],
            ["Drawdown Condition",     _sc(fs.get("drawdown_condition"))],
        ]
        fst = Table(fs_rows, colWidths=[5*cm, 12.5*cm])
        fst.setStyle(TableStyle([
            ("FONTSIZE",  (0,0), (-1,-1), 8),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT]),
            ("GRID",      (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",   (0,0), (-1,-1), 5),
        ]))
        story.append(fst); story.append(Spacer(1, 0.4*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 4 -- Five Cs Analysis
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("4. Five Cs Analysis", h1_style))
        five_cs_rows = [["Dimension", "Score", "Band", "Key Metrics"]]
        for key, label in [("character","Character"), ("capacity","Capacity"),
                            ("capital","Capital"), ("collateral","Collateral"),
                            ("conditions","Conditions")]:
            sc   = cam["five_cs"][key]["score"]
            band = "STRONG" if sc >= 70 else "ADEQUATE" if sc >= 50 else "WEAK"
            dets = cam["five_cs"][key]["details"]
            key_line = "  |  ".join(
                f"{d['metric']}: {d['value']}" for d in dets[:2] if d.get("value","N/A") != "N/A"
            )
            five_cs_rows.append([label, f"{sc:.0f}/100", band, _sc(key_line)])

        fct = Table(five_cs_rows, colWidths=[3.5*cm, 2.5*cm, 3*cm, 8.5*cm])
        fct.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 5),
        ]))
        story.append(fct); story.append(Spacer(1, 0.2*cm))

        # Five Cs detail sub-tables
        for key, label in [("character","Character"), ("capacity","Capacity"),
                            ("capital","Capital"), ("collateral","Collateral"),
                            ("conditions","Conditions")]:
            dets = cam["five_cs"][key]["details"]
            story.append(Paragraph(f"{label} Detail", h2_style))
            det_rows = [["Metric", "Value", "Note"]]
            for d in dets:
                det_rows.append([_sc(d.get("metric")), _sc(d.get("value")), _sc(d.get("unit",""))])
            dt = Table(det_rows, colWidths=[5.5*cm, 4*cm, 8*cm])
            dt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), TEAL),
                ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
                ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
                ("PADDING",    (0,0), (-1,-1), 4),
            ]))
            story.append(dt); story.append(Spacer(1, 0.15*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 5 -- Financial Ratios
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("5. Key Financial Ratios", h1_style))
        ratio_rows = [["Financial Metric", "Value", "Source Document", "Higher is Better"]]
        for r in cam["financial_ratios"]:
            ratio_rows.append([
                _sc(r.get("metric")), _sc(r.get("value")),
                _sc(r.get("source")),
                "Yes" if r.get("higher_is_better") else "No",
            ])
        rt = Table(ratio_rows, colWidths=[5.5*cm, 3*cm, 5*cm, 4*cm])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 5),
        ]))
        story.append(rt)
        story.append(Paragraph(
            "Note: 'N/A' indicates the ratio could not be extracted from the uploaded documents. "
            "The AI model uses conservative imputed values for scoring.",
            small_style,
        ))
        story.append(Spacer(1, 0.4*cm))

        # ═══════════════════════════════════════════════════════════════════════
        # Section 6 -- Fraud & Integrity Assessment
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("6. Fraud & Integrity Assessment", h1_style))
        fi = cam.get("fraud_integrity", {})
        overall_band = fi.get("overall_risk_band", "N/A")
        band_color = {"LOW": GREEN, "MEDIUM": AMBER, "HIGH": RED}.get(overall_band, NAVY)

        story.append(Paragraph(
            f"Integrity Score: <b>{fi.get('integrity_score','N/A')}/100</b>  |  "
            f"Overall Fraud Risk: <b>{overall_band}</b>  |  "
            f"Cross-Verification Severity: <b>{fi.get('overall_severity','N/A')}</b>",
            body_style,
        ))
        story.append(Spacer(1, 0.2*cm))

        fraud_rows = [
            ["Test", "Score", "Risk Band", "Interpretation"],
            ["Circular Trading Detection",
             _sc(fi.get("circular_trading",{}).get("score")),
             _sc(fi.get("circular_trading",{}).get("band")),
             _sc(fi.get("circular_trading",{}).get("detail")) or "Checks for round-trip fund flows"],
            ["Benford Law Deviation",
             _sc(fi.get("benford_deviation",{}).get("score")),
             _sc(fi.get("benford_deviation",{}).get("band")),
             _sc(fi.get("benford_deviation",{}).get("detail"))],
            ["GST vs Bank Revenue (mismatch %)",
             f"{_sc(fi.get('gst_bank_reconciliation',{}).get('mismatch_pct'))}%",
             _sc(fi.get("gst_bank_reconciliation",{}).get("band")),
             "Revenue reported in GST vs bank credits"],
            ["GSTR-2A vs 3B (mismatch %)",
             f"{_sc(fi.get('gstr_reconciliation',{}).get('mismatch_pct'))}%",
             _sc(fi.get("gstr_reconciliation",{}).get("band")),
             "ITC claimed vs eligible input tax credit"],
            ["ITR vs Annual Report (mismatch %)",
             f"{_sc(fi.get('itr_reconciliation',{}).get('mismatch_pct'))}%",
             _sc(fi.get("itr_reconciliation",{}).get("band")),
             "Income declared in ITR vs AR"],
        ]
        fat = Table(fraud_rows, colWidths=[5.5*cm, 2*cm, 2.5*cm, 7.5*cm])
        fat.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(fat)
        _raw_flags = fi.get("all_flags", []) + fi.get("fraud_flags", [])
        seen = set()
        all_flags = []
        for f in _raw_flags:
            key = str(f)
            if key not in seen:
                seen.add(key)
                all_flags.append(f)
        if all_flags:
            story.append(Spacer(1, 0.15*cm))
            story.append(Paragraph("Verification Flags:", h2_style))
            for flag in all_flags[:8]:
                story.append(Paragraph(f"* {flag}", body_style))
        story.append(Spacer(1, 0.4*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 7 -- Promoter & Governance
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("7. Promoter & Governance Profile", h1_style))
        pg = cam.get("promoter_governance", {})
        pg_rows = [
            ["Promoter Network Risk Score", f"{float(pg.get('risk_score') or 0):.3f}  (0-1, lower is better)"],
            ["Governance Risk Score",       f"{float(pg.get('governance_risk') or 0):.3f}  (0-1, lower is better)"],
            ["Character Score",             f"{float(pg.get('character_score') or 0):.1f} / 100"],
        ]
        pgt = Table(pg_rows, colWidths=[6*cm, 11.5*cm])
        pgt.setStyle(TableStyle([
            ("FONTSIZE",  (0,0), (-1,-1), 8),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT]),
            ("GRID",      (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",   (0,0), (-1,-1), 4),
        ]))
        story.append(pgt)
        for lbl, txt in [("Litigation Summary", pg.get("litigation_summary","")),
                          ("Network Summary",    pg.get("network_summary",""))]:
            if txt:
                story.append(Spacer(1, 0.15*cm))
                story.append(Paragraph(f"<b>{lbl}:</b> {txt}", body_style))
        audit_issues = pg.get("audit_issues", [])
        if audit_issues:
            story.append(Spacer(1, 0.1*cm))
            story.append(Paragraph("Audit & Red Flags:", h2_style))
            for issue in audit_issues[:5]:
                story.append(Paragraph(f"* {issue}", body_style))
        story.append(Spacer(1, 0.4*cm))

        # ═══════════════════════════════════════════════════════════════════════
        # Section 8 -- Sector Outlook
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("8. Sector & Macroeconomic Outlook", h1_style))
        so = cam.get("sector_outlook", {})
        story.append(Paragraph(
            f"Sector: <b>{so.get('sector_name','N/A')}</b>  |  "
            f"Sector Risk Score: <b>{so.get('risk_score',0):.3f}</b>  (0-1, lower is better)",
            body_style,
        ))
        if so.get("outlook"):
            story.append(Paragraph(so["outlook"], body_style))
        if so.get("regulatory_note"):
            story.append(Paragraph(f"Regulatory: {so['regulatory_note']}", small_style))

        benchmarks = so.get("benchmarks", {}).get("sector_medians", {})
        if benchmarks:
            story.append(Spacer(1, 0.15*cm))
            story.append(Paragraph("Sector Peer Benchmarks:", h2_style))
            bm_rows = [["Metric", "Company", "Sector Median", "vs. Peers"]]
            cmp = so.get("benchmarks", {}).get("company_vs_sector", {})
            for metric, med_val in benchmarks.items():
                co_val = cmp.get(metric, "N/A")
                if isinstance(co_val, dict):
                    co_disp = str(co_val.get("company", "N/A"))
                    vs      = co_val.get("vs_sector", "N/A")
                else:
                    co_disp = str(co_val)
                    vs      = "N/A"
                bm_rows.append([metric.replace("_"," ").title(), _sc(co_disp),
                                 _sc(med_val), _sc(vs)])
            bmt = Table(bm_rows, colWidths=[5*cm, 3.5*cm, 3.5*cm, 5.5*cm])
            bmt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), TEAL),
                ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 8),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
                ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
                ("PADDING",    (0,0), (-1,-1), 4),
            ]))
            story.append(bmt)
        story.append(Spacer(1, 0.4*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 9 -- AI Risk Attribution (SHAP)
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("9. AI Risk Attribution (SHAP Analysis)", h1_style))
        ai_attr = cam.get("ai_risk_attribution", {})
        story.append(Paragraph(
            f"Method: {ai_attr.get('method','N/A')}  |  "
            f"Expected baseline PD: {ai_attr.get('expected_value', 'N/A')}",
            small_style,
        ))
        img_bytes = _shap_waterfall_image(shap_result)
        if img_bytes:
            img_buf = io.BytesIO(img_bytes)
            story.append(RLImage(img_buf, width=16*cm, height=8*cm))
        else:
            story.append(Paragraph("SHAP chart unavailable (matplotlib not installed).", small_style))

        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("Interpretation (positive SHAP = increases default risk):", h2_style))
        for line in ai_attr.get("human_readable", [])[:10]:
            # Strip any raw internal notation
            clean = line.replace("increases_risk", "increases risk").replace("decreases_risk", "reduces risk")
            story.append(Paragraph(f"* {clean}", body_style))
        story.append(Spacer(1, 0.4*cm))

        # ═══════════════════════════════════════════════════════════════════════
        # Section 10 -- Evidence Traceability
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("10. Evidence Traceability", h1_style))
        story.append(Paragraph(
            "Each financial metric below is linked to its source document and section.",
            small_style,
        ))
        ev_rows = [["Metric", "Computed Value", "Source Document", "Document Section", "Top Driver"]]
        for row in cam.get("evidence_traceability", [])[:18]:
            is_top = "YES" if row.get("is_top_driver") else ""
            ev_rows.append([
                _sc(row.get("metric")), _sc(row.get("value")),
                _sc(row.get("source_doc")), _sc(row.get("section")), is_top,
            ])
        evt = Table(ev_rows, colWidths=[4.2*cm, 2.2*cm, 4.2*cm, 4.2*cm, 2.7*cm])
        evt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 7.5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 3),
        ]))
        story.append(evt)

        # Documents reviewed sub-table
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("Documents Reviewed:", h2_style))
        dr_rows = [["File Name", "Document Type", "Pages", "Extraction Confidence"]]
        for d in cam.get("documents_reviewed", []):
            conf = d.get("confidence", 0)
            conf_str = f"{conf:.0%}" if isinstance(conf, float) else str(conf)
            dr_rows.append([_sc(d.get("name")), _sc(d.get("type")), str(d.get("pages",0)), conf_str])
        drt = Table(dr_rows, colWidths=[6*cm, 4*cm, 2*cm, 5.5*cm])
        drt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), TEAL),
            ("TEXTCOLOR",  (0,0), (-1,0), WHITE),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(drt); story.append(Spacer(1, 0.4*cm))

        story.append(PageBreak())

        # ═══════════════════════════════════════════════════════════════════════
        # Section 11 -- Sanction Recommendation
        # ═══════════════════════════════════════════════════════════════════════
        story.append(Paragraph("11. Sanction Recommendation", h1_style))
        sr = cam.get("sanction_recommendation", {})
        story.append(Paragraph(sr.get("narrative",""), body_style))

        if sr.get("conditions"):
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph("Conditions Precedent to Sanction:", h2_style))
            for i, c in enumerate(sr["conditions"], 1):
                story.append(Paragraph(f"{i}. {c}", body_style))

        sr_rows = [
            ["AI Credit Score",    f"{sr.get('credit_score', 'N/A'):.1f}/100" if isinstance(sr.get('credit_score'),(int,float)) else "N/A"],
            ["Risk Grade",         _sc(sr.get("risk_grade"))],
            ["Probability of Default", f"{sr.get('pd',0):.1%}" if isinstance(sr.get('pd'),(int,float)) else "N/A"],
            ["Recommended Limit",  f"Rs. {_sc(sr.get('max_loan_cr'))} Cr"],
            ["Interest Rate",      f"{_sc(sr.get('rate_pct'))}% p.a."],
            ["Tenor",              f"{_sc(sr.get('tenure_years'))} years"],
            ["Review Frequency",   _sc(sr.get("review_frequency", "Annual"))],
        ]
        srt = Table(sr_rows, colWidths=[5*cm, 12.5*cm])
        srt.setStyle(TableStyle([
            ("FONTSIZE",  (0,0), (-1,-1), 8),
            ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT]),
            ("GRID",      (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",   (0,0), (-1,-1), 5),
        ]))
        story.append(Spacer(1, 0.2*cm)); story.append(srt)

        # ── Disclaimer ────────────────────────────────────────────────────────
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(sr.get("disclaimer",""), small_style))

        doc.build(story)
        logger.info(f"[PDF] CAM PDF saved -> {output_path}")
        return output_path
