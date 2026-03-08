"""
PDF Exporter — renders the CAM dict to a professional PDF using ReportLab.
Colour-coded decision block: GREEN=Approve, AMBER=Conditional, RED=Reject.
Embeds SHAP waterfall as a matplotlib PNG.
"""
from __future__ import annotations
import io
import os
from typing import Dict, Any
from loguru import logger

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ── Colour constants ─────────────────────────────────────────────────────────
GREEN  = colors.HexColor("#10B981")
AMBER  = colors.HexColor("#F59E0B")
RED    = colors.HexColor("#EF4444")
NAVY   = colors.HexColor("#1E3A5F")
LIGHT  = colors.HexColor("#F3F4F6")
WHITE  = colors.white
BLACK  = colors.black


def _verdict_color(verdict: str):
    if verdict == "APPROVE":            return GREEN
    if verdict == "CONDITIONAL_APPROVE": return AMBER
    return RED


def _shap_waterfall_image(shap_result: Dict) -> bytes | None:
    """Generate a horizontal bar chart of SHAP top-10 as PNG bytes."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        drivers = shap_result.get("top_drivers", [])[:10]
        if not drivers:
            return None

        names  = [d["feature"].replace("_", " ").title() for d in drivers]
        values = [d["shap_value"] for d in drivers]
        colors_bar = ["#EF4444" if v > 0 else "#10B981" for v in values]

        fig, ax = plt.subplots(figsize=(8, 4))
        y_pos = np.arange(len(names))
        ax.barh(y_pos, values, color=colors_bar, edgecolor="none", height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=8)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("SHAP Value (positive = increases default risk)", fontsize=8)
        ax.set_title("Top Risk Drivers — SHAP Attribution", fontsize=10, fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        logger.warning(f"[PDF] SHAP chart skipped: {e}")
        return None


class PDFExporter:

    def export(self, cam: Dict[str, Any], shap_result: Dict, output_path: str) -> str:
        logger.info(f"[PDF] Generating CAM PDF → {output_path}")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            topMargin=2*cm, bottomMargin=2*cm,
            leftMargin=2*cm, rightMargin=2*cm,
        )
        styles = getSampleStyleSheet()
        story  = []

        # Styles
        title_style  = ParagraphStyle("title",  fontSize=16, textColor=NAVY, spaceAfter=6, fontName="Helvetica-Bold", alignment=TA_CENTER)
        h1_style     = ParagraphStyle("h1",     fontSize=12, textColor=NAVY, spaceAfter=4, fontName="Helvetica-Bold")
        h2_style     = ParagraphStyle("h2",     fontSize=10, textColor=NAVY, spaceAfter=3, fontName="Helvetica-Bold")
        body_style   = ParagraphStyle("body",   fontSize=9,  spaceAfter=3,  fontName="Helvetica")
        small_style  = ParagraphStyle("small",  fontSize=8,  spaceAfter=2,  fontName="Helvetica", textColor=colors.grey)

        meta    = cam["meta"]
        dec     = cam["decision_block"]
        verdict = dec["verdict"]
        v_color = _verdict_color(verdict)

        # ── Cover / Letterhead ────────────────────────────────────────────────
        story.append(Paragraph("CREDIT APPRAISAL MEMORANDUM", title_style))
        story.append(Paragraph("Intelli-Credit AI Engine", small_style))
        story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
        story.append(Spacer(1, 0.3*cm))

        meta_data = [
            ["Company",        meta["company_name"],
             "Date",           meta["date"]],
            ["Loan Purpose",   meta["loan_purpose"],
             "Prepared by",    meta["prepared_by"]],
        ]
        mt = Table(meta_data, colWidths=[3.5*cm, 7*cm, 3*cm, 4*cm])
        mt.setStyle(TableStyle([
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("FONTNAME",   (0,0), (0,-1),  "Helvetica-Bold"),
            ("FONTNAME",   (2,0), (2,-1),  "Helvetica-Bold"),
            ("BACKGROUND", (0,0), (-1,-1), LIGHT),
            ("GRID",       (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.4*cm))

        # ── Decision Box ────────────────────────────────────────────────────
        verdict_display = verdict.replace("_", " ")
        loan_d = dec.get("loan_details", {})
        loan_line = ""
        if loan_d:
            loan_line = (
                f"Recommended Loan: ₹{loan_d.get('max_loan_crore','?')} Cr  |  "
                f"Rate: {loan_d.get('interest_rate_pct','?')}% p.a.  |  "
                f"Tenure: {loan_d.get('tenure_years','?')} years"
            )

        decision_data = [
            [Paragraph(f"<b>{verdict_display}</b>", ParagraphStyle("vd", fontSize=14, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER))],
            [Paragraph(f"Credit Score: {dec['credit_score']}  |  Risk Grade: {dec['risk_grade']}  |  PD: {dec['probability_default']:.2%}", ParagraphStyle("ds", fontSize=9, textColor=WHITE, alignment=TA_CENTER))],
            [Paragraph(loan_line, ParagraphStyle("ll", fontSize=8, textColor=WHITE, alignment=TA_CENTER))],
        ]
        dt = Table(decision_data, colWidths=[17*cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), v_color),
            ("PADDING",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [v_color]),
        ]))
        story.append(dt)
        story.append(Spacer(1, 0.4*cm))

        # ── Executive Summary ─────────────────────────────────────────────────
        story.append(Paragraph("Executive Summary", h1_style))
        story.append(Paragraph(cam["executive_summary"], body_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Conditions ────────────────────────────────────────────────────────
        conds = dec.get("conditions", [])
        if conds:
            story.append(Paragraph("Conditions Precedent / Subsequent", h1_style))
            for i, c in enumerate(conds, 1):
                story.append(Paragraph(f"{i}. {c}", body_style))
            story.append(Spacer(1, 0.3*cm))

        # ── Five Cs ───────────────────────────────────────────────────────────
        story.append(Paragraph("Five Cs Analysis", h1_style))
        five_cs_rows = [["Dimension", "Score", "Assessment"]]
        for key, label in [("character","Character"), ("capacity","Capacity"),
                           ("capital","Capital"), ("collateral","Collateral"),
                           ("conditions","Conditions")]:
            sc = cam["five_cs"][key]["score"]
            band = "Strong" if sc >= 70 else "Adequate" if sc >= 50 else "Weak"
            five_cs_rows.append([label, f"{sc:.0f}/100", band])

        fct = Table(five_cs_rows, colWidths=[5*cm, 4*cm, 8*cm])
        fct.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",     (0,0), (-1,-1), 5),
        ]))
        story.append(fct)
        story.append(Spacer(1, 0.4*cm))

        # ── Financial Ratios ─────────────────────────────────────────────────
        story.append(Paragraph("Key Financial Ratios", h1_style))
        ratio_rows = [["Metric", "Value"]]
        for r in cam["financial_ratios"]:
            ratio_rows.append([r["metric"], r["value"]])
        rt = Table(ratio_rows, colWidths=[10*cm, 7*cm])
        rt.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",     (0,0), (-1,-1), 5),
        ]))
        story.append(rt)
        story.append(Spacer(1, 0.3*cm))

        # ── SHAP Chart ────────────────────────────────────────────────────────
        story.append(Paragraph("AI Risk Attribution (SHAP)", h1_style))
        img_bytes = _shap_waterfall_image(shap_result)
        if img_bytes:
            img_buf = io.BytesIO(img_bytes)
            rl_img  = RLImage(img_buf, width=16*cm, height=8*cm)
            story.append(rl_img)
        else:
            story.append(Paragraph("SHAP chart not available.", body_style))

        narrative = shap_result.get("human_readable", [])
        for line in narrative[:8]:
            story.append(Paragraph(f"• {line}", small_style))
        story.append(Spacer(1, 0.4*cm))

        # ── Fraud Assessment ──────────────────────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("Fraud & Integrity Assessment", h1_style))
        fa = cam["fraud_assessment"]
        fraud_data = [
            ["Fraud Risk Score", f"{fa['fraud_risk_score']:.1f}/100"],
            ["Circular Trading Score", f"{fa['circular_trading_score']:.3f}"],
            ["Benford Deviation", f"{fa['benford_deviation']:.3f}"],
        ]
        fat = Table(fraud_data, colWidths=[8*cm, 9*cm])
        fat.setStyle(TableStyle([
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("FONTNAME",    (0,0), (0,-1),  "Helvetica-Bold"),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [WHITE, LIGHT]),
            ("PADDING",     (0,0), (-1,-1), 5),
        ]))
        story.append(fat)
        if fa["flags"]:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph("Fraud Flags:", h2_style))
            for flag in fa["flags"]:
                story.append(Paragraph(f"• {flag}", body_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Verification Findings ─────────────────────────────────────────────
        story.append(Paragraph("Cross-Verification Findings", h1_style))
        vf = cam["verification_findings"]
        story.append(Paragraph(f"Overall Severity: <b>{vf['overall_severity']}</b>", body_style))
        all_flags = vf["gst_bank_flags"] + vf["itr_flags"] + vf["gstr_flags"]
        if all_flags:
            for flag in all_flags:
                story.append(Paragraph(f"• {flag}", body_style))
        else:
            story.append(Paragraph("No significant cross-verification discrepancies detected.", body_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Promoter Profile ──────────────────────────────────────────────────
        story.append(Paragraph("Promoter & Management Profile", h1_style))
        pp = cam["promoter_profile"]
        story.append(Paragraph(f"Promoter Network Risk Score: <b>{pp['risk_score']:.2f}</b>", body_style))
        story.append(Paragraph(pp.get("litigation_summary", ""), body_style))
        story.append(Paragraph(pp.get("network_summary", ""), body_style))
        story.append(Spacer(1, 0.3*cm))

        # ── Sector Outlook ────────────────────────────────────────────────────
        story.append(Paragraph("Sector & Macroeconomic Outlook", h1_style))
        so = cam["sector_outlook"]
        story.append(Paragraph(f"Sector: <b>{so['sector_name']}</b>  |  Risk Score: <b>{so['risk_score']:.2f}</b>", body_style))
        story.append(Paragraph(so.get("outlook", ""), body_style))
        story.append(Spacer(1, 0.3*cm))

        # ── AI Risk Narrative ─────────────────────────────────────────────────
        risk_narr = cam.get("risk_narrative", "")
        if risk_narr:
            story.append(Paragraph("AI Risk Assessment", h1_style))
            story.append(Paragraph(risk_narr, body_style))
            story.append(Spacer(1, 0.3*cm))

        # ── Documents Reviewed ────────────────────────────────────────────────
        story.append(Paragraph("Documents Reviewed", h1_style))
        dr = [["File Name", "Type", "Pages", "Confidence"]]
        for d in cam["documents_reviewed"]:
            dr.append([d["name"], d["type"], str(d["pages"]), f"{d['confidence']:.0%}"])
        drt = Table(dr, colWidths=[6*cm, 4*cm, 2.5*cm, 4.5*cm])
        drt.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  NAVY),
            ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("PADDING",     (0,0), (-1,-1), 4),
        ]))
        story.append(drt)
        story.append(Spacer(1, 0.5*cm))

        # ── Footer disclaimer ─────────────────────────────────────────────────
        rec_note = cam.get("recommendation_note", "")
        if rec_note:
            story.append(Paragraph("Sanctioning Committee Recommendation", h1_style))
            story.append(Paragraph(rec_note, body_style))
            story.append(Spacer(1, 0.3*cm))

        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Paragraph(
            "DISCLAIMER: This Credit Appraisal Memo has been generated by an AI system. "
            "All outputs are indicative and must be reviewed by a qualified credit officer before "
            "any credit decision is executed. This document does not constitute a binding commitment.",
            small_style,
        ))

        doc.build(story)
        logger.info(f"[PDF] CAM PDF saved → {output_path}")
        return output_path
