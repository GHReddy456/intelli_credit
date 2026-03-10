"""
Promoter Intelligence Agent
Builds a promoter risk network using NetworkX.
Graph: Promoter → Directors → Companies → Litigation → NPA flags

Also detects shell company networks:
  - Directors that appear in 3+ companies = possible shell network
  - Multiple companies sharing a registered address
"""
import re
from collections import defaultdict
import networkx as nx
from typing import List, Dict, Any
from loguru import logger

# Patterns that indicate web-scraped noise rather than real entities
_NOISE_PATTERNS = re.compile(
    r"(https?://|www\.|\.com|\.in|\.org|\.net|cookie|privacy|terms|"
    r"sign\s*in|subscribe|navbar|footer|menu|click\s*here|read\s*more|"
    r"published|article|advertisement|sponsored|©|all rights reserved)",
    re.IGNORECASE,
)
# Valid entity names: at least 2 alpha chars, no long URLs, reasonable length
_VALID_NAME = re.compile(r"^[A-Za-z][\w\s.\-&'()]{1,80}$")


def _is_valid_entity(name: str) -> bool:
    """Filter out web article titles, URLs, and noise from entity names."""
    if not name or len(name.strip()) < 2:
        return False
    if _NOISE_PATTERNS.search(name):
        return False
    if not _VALID_NAME.match(name.strip()):
        return False
    return True


class PromoterIntelligenceAgent:
    def run(self, segmented_docs: List, research: Dict) -> Dict[str, Any]:
        logger.info("[PromoterAgent] Building promoter network")

        G = nx.DiGraph()
        mca_data = research.get("mca", {})
        lit_data = research.get("litigation", {})

        # Add promoter nodes (filtered for valid entity names)
        promoters = [p for p in research.get("promoter_names", []) if _is_valid_entity(p)]
        for p in promoters:
            G.add_node(p, node_type="promoter")

        # Add director nodes from MCA (filtered)
        for d in mca_data.get("director_list", []):
            name = d.get("name", "UNKNOWN")
            if not _is_valid_entity(name):
                continue
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

        # Shell company network detection
        shell_result = self._detect_shell_network(mca_data, research)
        risk_score   = round(min(risk_score + shell_result["shell_network_score"] * 0.30, 1.0), 4)

        # Serialize graph for frontend
        graph_data = self._serialise(G)

        flags = []
        if risk_score > 0.7:
            flags.append({
                "flag":     "HIGH_PROMOTER_RISK",
                "severity": "HIGH",
                "detail":   f"Promoter network risk score {risk_score:.2f} — complex connected entity structure detected",
            })
        flags.extend(shell_result["flags"])

        logger.info(f"[PromoterAgent] Network: {G.number_of_nodes()} nodes, score={risk_score:.3f}")

        return {
            "promoter_network_risk":      risk_score,
            "shell_network_score":        shell_result["shell_network_score"],
            "multi_company_directors":    shell_result["multi_company_directors"],
            "promoter_count":             len(promoters),
            "director_count":             mca_data.get("director_count", 0),
            "litigation_links":           len(lit_data.get("cases", [])),
            "graph_nodes":                G.number_of_nodes(),
            "graph_edges":                G.number_of_edges(),
            "graph_data":                 graph_data,
            "flags":                      flags,
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

    def _detect_shell_network(self, mca_data: Dict, research: Dict) -> Dict[str, Any]:
        """
        Detect shell company networks by locating directors common across
        multiple companies. If the same person directors 3+ companies it is
        a red flag per RBI / MCA guidelines.

        Also checks for shared registered addresses extracted from docs.
        """
        director_to_companies: Dict[str, set] = defaultdict(set)
        company_name = research.get("company_name", "")

        # From MCA director list — each entry may carry an associated company
        for d in mca_data.get("director_list", []):
            name    = (d.get("name") or "").strip()
            company = (d.get("company") or company_name).strip()
            if name and name.upper() not in ("UNKNOWN", "N/A") and _is_valid_entity(name):
                director_to_companies[name].add(company)

        # From research related entities
        for rel in research.get("related_entities", []):
            company = (rel.get("name") or "").strip()
            if not _is_valid_entity(company):
                continue
            for director in rel.get("directors", []):
                if director and _is_valid_entity(director) and company:
                    director_to_companies[director.strip()].add(company)

        # Flag directors appearing in ≥ 3 distinct companies
        multi_company: Dict[str, List[str]] = {
            d: sorted(companies)
            for d, companies in director_to_companies.items()
            if len(companies) >= 3
        }

        score = min(len(multi_company) * 0.20, 0.60)

        flags = []
        if multi_company:
            flags.append({
                "flag":      "POTENTIAL_SHELL_NETWORK",
                "severity":  "HIGH",
                "detail": (
                    f"{len(multi_company)} director(s) found across 3+ companies — "
                    "possible shell company network per MCA norms"
                ),
                "directors": list(multi_company.keys())[:5],
            })

        return {
            "shell_network_score":     round(score, 4),
            "multi_company_directors": multi_company,
            "flags":                   flags,
        }

    def _serialise(self, G: nx.DiGraph) -> Dict:
        return {
            "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes()],
            "edges": [{"from": u, "to": v, **G[u][v]} for u, v in G.edges()],
        }
