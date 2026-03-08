"""
Promoter Intelligence Agent
Builds a promoter risk network using NetworkX.
Graph: Promoter → Directors → Companies → Litigation → NPA flags
"""
import re
import networkx as nx
from typing import List, Dict, Any
from loguru import logger


class PromoterIntelligenceAgent:
    def run(self, segmented_docs: List, research: Dict) -> Dict[str, Any]:
        logger.info("[PromoterAgent] Building promoter network")

        G = nx.DiGraph()
        mca_data = research.get("mca", {})
        lit_data = research.get("litigation", {})

        # Add promoter nodes
        promoters = research.get("promoter_names", [])
        for p in promoters:
            G.add_node(p, node_type="promoter")

        # Add director nodes from MCA
        for d in mca_data.get("director_list", []):
            name = d.get("name", "UNKNOWN")
            G.add_node(name, node_type="director")
            for p in promoters:
                G.add_edge(p, name, relation="is_director")

        # Add litigation nodes
        for case in lit_data.get("cases", []):
            case_id = case.get("summary", "")[:40]
            G.add_node(case_id, node_type="litigation", severity=case.get("severity", "LOW"))
            for p in promoters:
                G.add_edge(p, case_id, relation="involved_in")

        # Add company charges from MCA
        for charge in mca_data.get("company_charges", []):
            lender = charge.get("lender", "UNKNOWN")
            G.add_node(lender, node_type="lender")
            for p in promoters:
                G.add_edge(p, lender, relation="borrowed_from")

        # Score the promoter risk
        risk_score = self._score_promoter_risk(G, promoters, mca_data, lit_data)

        # Serialize graph for frontend
        graph_data = self._serialise(G)

        flags = []
        if risk_score > 0.7:
            flags.append({
                "flag":     "HIGH_PROMOTER_RISK",
                "severity": "HIGH",
                "detail":   f"Promoter network risk score {risk_score:.2f} — complex connected entity structure detected",
            })

        logger.info(f"[PromoterAgent] Network: {G.number_of_nodes()} nodes, score={risk_score:.3f}")

        return {
            "promoter_network_risk":  risk_score,
            "promoter_count":         len(promoters),
            "director_count":         mca_data.get("director_count", 0),
            "litigation_links":       len(lit_data.get("cases", [])),
            "graph_nodes":            G.number_of_nodes(),
            "graph_edges":            G.number_of_edges(),
            "graph_data":             graph_data,
            "flags":                  flags,
        }

    def _score_promoter_risk(self, G: nx.DiGraph, promoters: List, mca: Dict, lit: Dict) -> float:
        score = 0.0

        # Litigation severity
        score += min(lit.get("litigation_severity_score", 0.0) * 0.5, 0.40)

        # High-severity cases
        high_cases = lit.get("high_severity_count", 0)
        score += min(high_cases * 0.10, 0.30)

        # Disqualified director
        if mca.get("disqualification_flag"):
            score += 0.30

        # Large network = more risk in Indian context
        if G.number_of_nodes() > 20:
            score += 0.10

        return round(min(score, 1.0), 4)

    def _serialise(self, G: nx.DiGraph) -> Dict:
        return {
            "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes()],
            "edges": [{"from": u, "to": v, **G[u][v]} for u, v in G.edges()],
        }
