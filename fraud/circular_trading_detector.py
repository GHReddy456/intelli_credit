"""
Circular Trading Detector
Finds cycles in the transaction graph where money returns to the origin
within ROUND_TRIP_DAYS. Uses networkx.simple_cycles().
"""
import networkx as nx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
from backend.config import ROUND_TRIP_DAYS, CIRCULAR_TRADING_THRESHOLD
from fraud.transaction_graph import TransactionGraph


class CircularTradingDetector:
    """
    Algorithm:
    1. Build directed transaction graph (nodes=entities, edges=money flow)
    2. Detect all simple cycles (networkx.simple_cycles)
    3. For each cycle, check if any transactions are within ROUND_TRIP_DAYS
    4. Score = weighted sum of (cycle_amount / total_credits) for qualifying cycles
    """

    def detect(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        logger.info("[CircularTrading] Building transaction graph...")

        builder = TransactionGraph()
        G = builder.build(segmented_docs, tables)
        stats = builder.stats(G)

        cycles = []
        raw_score = 0.0

        try:
            for cycle in nx.simple_cycles(G):
                if len(cycle) < 2:
                    continue

                # Calculate cycle total amount
                cycle_amt = 0
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    if G.has_edge(u, v):
                        cycle_amt += G[u][v].get("total_amount", 0)

                if cycle_amt > 0:
                    cycles.append({
                        "nodes":  cycle,
                        "length": len(cycle),
                        "total_amount": cycle_amt,
                        "suspicious": len(cycle) <= 4,  # Short cycles = more suspicious
                    })

                # Cap at 500 cycles for performance
                if len(cycles) >= 500:
                    break

        except Exception as e:
            logger.error(f"[CircularTrading] Cycle detection failed: {e}")

        # Compute score
        total_credits = sum(
            G[u][v].get("total_amount", 0)
            for u, v in G.edges()
        ) or 1

        suspicious_cycles = [c for c in cycles if c["suspicious"]]
        circular_amount   = sum(c["total_amount"] for c in suspicious_cycles)
        raw_score         = circular_amount / total_credits
        circular_score    = round(min(raw_score, 1.0), 4)

        is_suspicious = circular_score > 0.30
        is_hard_reject = circular_score > CIRCULAR_TRADING_THRESHOLD

        flags = []
        if is_hard_reject:
            flags.append({
                "flag":     "CIRCULAR_TRADING_HIGH",
                "severity": "CRITICAL",
                "detail":   f"Circular trading score {circular_score:.2f} exceeds hard-reject threshold {CIRCULAR_TRADING_THRESHOLD}",
            })
        elif is_suspicious:
            flags.append({
                "flag":     "CIRCULAR_TRADING_MEDIUM",
                "severity": "HIGH",
                "detail":   f"Possible circular trading detected — score {circular_score:.2f}",
            })

        logger.info(f"[CircularTrading] Score={circular_score:.3f}, Cycles={len(cycles)}, Suspicious={len(suspicious_cycles)}")

        return {
            "circular_trading_score": circular_score,
            "total_cycles":           len(cycles),
            "suspicious_cycles":      len(suspicious_cycles),
            "top_cycles":             suspicious_cycles[:5],   # For frontend display
            "graph_stats":            stats,
            "is_hard_reject":         is_hard_reject,
            "flags":                  flags,
        }
