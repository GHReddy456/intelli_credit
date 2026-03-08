"""
Evidence Graph — traces how uploaded documents feed into computed features and final decision.
Serialised to JSON for the EvidenceViewer React component.
"""
from __future__ import annotations
import json
from typing import Dict, Any, List
import networkx as nx
from loguru import logger


class EvidenceGraph:
    """
    Graph layers:
      Document → Segment/Table → Feature → Flag/Finding → Decision
    """

    def build(
        self,
        doc_summaries:    List[Dict],
        segment_summaries: List[Dict],
        features:          Dict[str, float],
        rule_result:       Dict[str, Any],
        ml_result:         Dict[str, Any],
        shap_result:       Dict[str, Any],
        decision:          str,
    ) -> Dict[str, Any]:

        G = nx.DiGraph()

        # ── Layer 0: DECISION node ──────────────────────────────────────────
        G.add_node("DECISION",
                   label=f"Decision: {decision}",
                   node_type="decision",
                   color="#10B981" if decision == "APPROVE" else ("#F59E0B" if decision == "CONDITIONAL_APPROVE" else "#EF4444"))

        # ── Layer 1: Document nodes ─────────────────────────────────────────
        for doc in doc_summaries:
            doc_id = f"DOC::{doc.get('file_name', 'unknown')}"
            G.add_node(doc_id, label=doc.get("file_name", "?"), node_type="document",
                       color="#6366F1", doc_type=doc.get("doc_type", "unknown"))

        # ── Layer 2: Segment nodes + edges from docs ────────────────────────
        for seg in segment_summaries:
            for section_label, section_data in (seg.get("sections", {}) or {}).items():
                seg_id = f"SEG::{seg.get('file_name','')}::{section_label}"
                G.add_node(seg_id, label=section_label.replace("_", " ").title(),
                           node_type="segment", color="#8B5CF6",
                           word_count=section_data.get("word_count", 0))
                doc_id = f"DOC::{seg.get('file_name','')}"
                if doc_id in G.nodes:
                    G.add_edge(doc_id, seg_id, rel="contains")

        # ── Layer 3: Feature nodes ──────────────────────────────────────────
        feature_to_docs: Dict[str, List[str]] = {
            "dscr":                      ["bank_statement", "annual_report"],
            "debt_to_equity":            ["annual_report"],
            "interest_coverage_ratio":   ["annual_report"],
            "current_ratio":             ["annual_report"],
            "revenue_growth_3yr":        ["annual_report", "itr"],
            "gst_bank_mismatch_score":   ["gst", "bank_statement"],
            "gstr2a_3b_mismatch_score":  ["gst"],
            "itr_revenue_mismatch_score":["itr", "annual_report"],
            "circular_trading_score":    ["bank_statement"],
            "benford_deviation_score":   ["bank_statement", "annual_report"],
            "litigation_severity_score": ["legal"],
            "news_sentiment_score":      ["external_news"],
            "promoter_network_risk":     ["annual_report", "mca"],
        }

        shap_top_names = {d["feature"] for d in shap_result.get("top_drivers", [])}

        for feat_name, feat_val in features.items():
            f_id = f"FEAT::{feat_name}"
            is_top = feat_name in shap_top_names
            G.add_node(f_id, label=feat_name.replace("_", " ").title(),
                       node_type="feature", value=round(feat_val, 4),
                       is_top_driver=is_top, color="#EC4899" if is_top else "#D1D5DB")

            # Connect segments → feature based on heuristic doc_type mapping
            related_dt = feature_to_docs.get(feat_name, [])
            connected = False
            for seg in segment_summaries:
                seg_dt = seg.get("doc_type", "")
                if any(dt in seg_dt for dt in related_dt):
                    for section_label in list((seg.get("sections") or {}).keys())[:2]:
                        seg_id = f"SEG::{seg.get('file_name','')}::{section_label}"
                        if seg_id in G.nodes:
                            G.add_edge(seg_id, f_id, rel="feeds")
                            connected = True
                            break
            # Fall-back: connect any doc if nothing else
            if not connected and doc_summaries:
                doc_id = f"DOC::{doc_summaries[0].get('file_name','')}"
                if doc_id in G.nodes:
                    G.add_edge(doc_id, f_id, rel="feeds")

        # ── Layer 3a: Hard reject flags ──────────────────────────────────────
        for flag in rule_result.get("hard_reject_flags", []):
            flag_id = f"FLAG::HR::{flag.get('rule','?')}"
            G.add_node(flag_id, label=f"HARD REJECT: {flag.get('rule','?')}",
                       node_type="hard_flag", color="#EF4444")
            f_id = f"FEAT::{flag.get('feature','')}"
            if f_id in G.nodes:
                G.add_edge(f_id, flag_id, rel="triggers")
            G.add_edge(flag_id, "DECISION", rel="determines")

        # ── Layer 3b: Policy flags ───────────────────────────────────────────
        for flag in rule_result.get("policy_flags", []):
            flag_id = f"FLAG::POLICY::{flag.get('rule','?')}"
            G.add_node(flag_id, label=f"{flag.get('rule','?')} (-{flag.get('deduction',0)}pts)",
                       node_type="policy_flag", color="#F59E0B")
            f_id = f"FEAT::{flag.get('feature','')}"
            if f_id in G.nodes:
                G.add_edge(f_id, flag_id, rel="triggers")
            G.add_edge(flag_id, "DECISION", rel="influences")

        # ── Layer 4: ML node ─────────────────────────────────────────────────
        ml_id = "ML::XGBoost"
        G.add_node(ml_id,
                   label=f"ML Score {ml_result.get('credit_score', '?')} | Grade {ml_result.get('risk_grade','?')}",
                   node_type="ml_model", color="#0EA5E9",
                   pod=ml_result.get("probability_of_default", 0))
        for feat_name in shap_top_names:
            f_id = f"FEAT::{feat_name}"
            if f_id in G.nodes:
                G.add_edge(f_id, ml_id, rel="input")
        G.add_edge(ml_id, "DECISION", rel="informs")

        # ── Serialise ────────────────────────────────────────────────────────
        nodes_data = []
        for nid, data in G.nodes(data=True):
            nodes_data.append({"id": nid, **data})

        links_data = []
        for src, dst, data in G.edges(data=True):
            links_data.append({"source": src, "target": dst, **data})

        logger.info(f"[EvidenceGraph] Built {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        return {
            "nodes": nodes_data,
            "links": links_data,
            "stats": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "layers":      ["document", "segment", "feature", "ml_model", "hard_flag", "policy_flag", "decision"],
            },
        }
