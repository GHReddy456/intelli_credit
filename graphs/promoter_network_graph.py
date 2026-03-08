"""
Promoter Network Graph Visualizer — serialises the promoter DiGraph built by
agents/promoter_intelligence_agent.py into D3 force-directed JSON.
"""
from __future__ import annotations
from typing import Dict, Any
import networkx as nx
from loguru import logger


NODE_COLORS = {
    "promoter":   "#7C3AED",
    "director":   "#6366F1",
    "company":    "#0EA5E9",
    "litigation": "#EF4444",
    "bank":       "#10B981",
    "lender":     "#10B981",
    "unknown":    "#9CA3AF",
}


class PromoterNetworkGraphVisualizer:

    def to_d3(self, G: nx.DiGraph) -> Dict[str, Any]:
        logger.info(f"[PromoterGraph] Serialising {G.number_of_nodes()} nodes")

        nodes = []
        for nid, data in G.nodes(data=True):
            ntype = data.get("type", "unknown")
            nodes.append({
                "id":     nid,
                "label":  data.get("name", str(nid)[:30]),
                "type":   ntype,
                "color":  NODE_COLORS.get(ntype, NODE_COLORS["unknown"]),
                "risk":   data.get("risk_score", 0),
                "radius": 14 if ntype == "promoter" else 10 if ntype == "director" else 8,
            })

        links = []
        for src, dst, data in G.edges(data=True):
            links.append({
                "source": src,
                "target": dst,
                "rel":    data.get("relationship", "related_to"),
                "color":  "#DC2626" if "litigation" in str(dst).lower() else "#CBD5E1",
                "dashed": data.get("relationship") == "litigation",
            })

        # Compute centrality to rank risk nodes
        try:
            dc = nx.degree_centrality(G)
        except Exception:
            dc = {n: 0 for n in G.nodes}

        high_risk_nodes = sorted(
            [(n, dc[n]) for n in G.nodes
             if G.nodes[n].get("type") in ("litigation","lender")],
            key=lambda x: -x[1],
        )[:5]

        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_nodes":     G.number_of_nodes(),
                "total_edges":     G.number_of_edges(),
                "promoter_count":  sum(1 for _, d in G.nodes(data=True) if d.get("type") == "promoter"),
                "litigation_count": sum(1 for _, d in G.nodes(data=True) if d.get("type") == "litigation"),
                "high_risk_nodes": [n for n, _ in high_risk_nodes],
            },
        }
