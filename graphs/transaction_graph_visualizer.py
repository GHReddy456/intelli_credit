"""
Transaction Graph Visualizer — serialises the fraud NetworkX DiGraph into a
D3.js-friendly force-directed JSON structure.
Highlights circular trading cycles with distinct colour coding.
"""
from __future__ import annotations
from typing import Dict, Any
import networkx as nx
from loguru import logger


class TransactionGraphVisualizer:

    def to_d3(self, G: nx.DiGraph, circular_cycles: list) -> Dict[str, Any]:
        """Convert transaction graph to D3 force JSON."""
        logger.info(f"[TxGraph] Serialising {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        # Flatten all cycle nodes for colour coding
        cycle_node_set = set()
        for cycle in circular_cycles:
            cycle_node_set.update(cycle)

        nodes = []
        node_index = {}
        for i, (nid, data) in enumerate(G.nodes(data=True)):
            node_index[nid] = i
            is_cycle = nid in cycle_node_set
            nodes.append({
                "id":        nid,
                "label":     data.get("name", str(nid)),
                "type":      data.get("entity_type", "unknown"),
                "inCycle":   is_cycle,
                "color":     "#EF4444" if is_cycle else "#6366F1",
                "radius":    12 if is_cycle else 8,
            })

        links = []
        for src, dst, data in G.edges(data=True):
            is_cycle_edge = (src in cycle_node_set and dst in cycle_node_set)
            links.append({
                "source":     src,
                "target":     dst,
                "amount":     round(data.get("amount", 0), 2),
                "date":       str(data.get("date", "")),
                "isCycle":    is_cycle_edge,
                "color":      "#EF4444" if is_cycle_edge else "#9CA3AF",
                "strokeWidth": 3 if is_cycle_edge else 1,
            })

        # Cycle summary list
        cycle_summaries = []
        for cycle in circular_cycles[:20]:   # Cap at 20 for UI
            cycle_summaries.append({
                "nodes":  cycle,
                "length": len(cycle),
                "risk":   "HIGH" if len(cycle) <= 3 else "MEDIUM",
            })

        return {
            "nodes":          nodes,
            "links":          links,
            "cycle_summaries": cycle_summaries,
            "stats": {
                "total_nodes":    G.number_of_nodes(),
                "total_edges":    G.number_of_edges(),
                "cycle_count":    len(circular_cycles),
                "cycle_nodes":    len(cycle_node_set),
            },
        }
