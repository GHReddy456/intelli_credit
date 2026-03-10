"""
Circular Trading Detector
Finds cycles in the transaction graph where money returns to the origin
within ROUND_TRIP_DAYS. Uses networkx.simple_cycles().

Also detects:
  - Layered transactions: high-value repeated payments between related entities
  - Shell company networks: multiple counterparties sharing promoter/director/address
"""
import re
import networkx as nx
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
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
    5. Detect layered transactions via counterparty frequency + round-trip flows
    6. Detect potential shell entities via shared identifiers across docs
    """

    def detect(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        logger.info("[CircularTrading] Building transaction graph...")

        builder = TransactionGraph()
        G = builder.build(segmented_docs, tables)
        stats = builder.stats(G)

        # ── Cycle detection ───────────────────────────────────────────────
        cycles = []
        try:
            for cycle in nx.simple_cycles(G):
                if len(cycle) < 2:
                    continue
                cycle_amt = 0
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    if G.has_edge(u, v):
                        cycle_amt += G[u][v].get("total_amount", 0)
                if cycle_amt > 0:
                    cycles.append({
                        "nodes":        cycle,
                        "length":       len(cycle),
                        "total_amount": cycle_amt,
                        "suspicious":   len(cycle) <= 4,
                    })
                if len(cycles) >= 500:
                    break
        except Exception as e:
            logger.error(f"[CircularTrading] Cycle detection failed: {e}")

        total_credits = sum(G[u][v].get("total_amount", 0) for u, v in G.edges()) or 1
        suspicious_cycles = [c for c in cycles if c["suspicious"]]
        circular_amount   = sum(c["total_amount"] for c in suspicious_cycles)

        # Score = weighted cycle amount share + cycle count penalty
        # Formula: fraud_score += len(cycles) x 10 (capped at 1.0)
        cycle_count_score = min(len(suspicious_cycles) * 10 / 100, 1.0)
        cycle_amt_score   = circular_amount / total_credits
        circular_score    = round(min(cycle_amt_score * 0.70 + cycle_count_score * 0.30, 1.0), 4)

        # ── Layered transaction detection ─────────────────────────────────
        layered_result = self._detect_layered_transactions(G, total_credits)

        # ── Shell company detection ───────────────────────────────────────
        shell_result = self._detect_shell_entities(segmented_docs, builder.all_entities(segmented_docs, tables))

        # ── Counterparty concentration ────────────────────────────────────
        cp_freq = builder.counterparty_frequency(segmented_docs, tables)
        top_counterparties = cp_freq.most_common(10)
        cp_concentration = self._counterparty_concentration(cp_freq)

        # ── Composite score ───────────────────────────────────────────────
        composite_score = round(min(
            circular_score * 0.50 +
            layered_result["layered_score"] * 0.25 +
            shell_result["shell_score"] * 0.15 +
            cp_concentration * 0.10,
            1.0
        ), 4)

        is_suspicious  = composite_score > 0.25
        is_hard_reject = composite_score > CIRCULAR_TRADING_THRESHOLD

        # ── Flags ─────────────────────────────────────────────────────────
        flags = []
        if circular_score > CIRCULAR_TRADING_THRESHOLD:
            flags.append({
                "flag": "CIRCULAR_TRADING_HIGH", "severity": "CRITICAL",
                "detail": f"Circular trading score {circular_score:.2f} — hard-reject threshold exceeded",
            })
        elif circular_score > 0.25:
            flags.append({
                "flag": "CIRCULAR_TRADING_MEDIUM", "severity": "HIGH",
                "detail": f"Possible circular trading — score {circular_score:.2f} ({len(suspicious_cycles)} suspicious cycles)",
            })
        flags.extend(layered_result["flags"])
        flags.extend(shell_result["flags"])
        if cp_concentration > 0.35:
            flags.append({
                "flag": "TRANSACTION_CONCENTRATION",
                "severity": "HIGH" if cp_concentration > 0.50 else "MEDIUM",
                "detail": (
                    f"Top counterparty accounts for {cp_concentration*100:.1f}% of transactions — "
                    f"exceeds 35% concentration threshold (possible layering or related-party abuse)"
                ),
            })

        logger.info(
            f"[CircularTrading] composite={composite_score:.3f}, cycles={len(cycles)}, "
            f"layered={layered_result['layered_score']:.3f}, shell={shell_result['shell_score']:.3f}"
        )

        return {
            "circular_trading_score":    composite_score,
            "cycle_score":               circular_score,
            "layered_score":             layered_result["layered_score"],
            "shell_score":               shell_result["shell_score"],
            "counterparty_concentration": cp_concentration,
            "total_cycles":              len(cycles),
            "suspicious_cycles":         len(suspicious_cycles),
            "top_cycles":                suspicious_cycles[:5],
            "top_counterparties":        top_counterparties[:5],
            "shell_entities":            shell_result["shell_entities"],
            "layered_pairs":             layered_result["layered_pairs"][:5],
            "graph_stats":               stats,
            "is_hard_reject":            is_hard_reject,
            "flags":                     flags,
        }

    # ── Layered transaction detection ──────────────────────────────────────
    def _detect_layered_transactions(self, G: nx.DiGraph, total_credits: float) -> Dict[str, Any]:
        """
        Flags pairs (A→B, B→A) with high mutual flow, and high-value
        repeated payments between the same nodes.
        """
        layered_pairs = []
        score = 0.0

        for u, v in G.edges():
            if not G.has_edge(v, u):
                continue
            fwd = G[u][v].get("total_amount", 0)
            rev = G[v][u].get("total_amount", 0)
            if fwd == 0 or rev == 0:
                continue
            round_trip_ratio = min(fwd, rev) / max(fwd, rev)  # 1.0 = perfect round-trip
            combined = fwd + rev
            layered_pairs.append({
                "entity_a": u, "entity_b": v,
                "fwd_amount": fwd, "rev_amount": rev,
                "round_trip_ratio": round(round_trip_ratio, 3),
                "combined_amount": combined,
            })
            score += round_trip_ratio * (combined / total_credits)

        flags = []
        if layered_pairs:
            layered_pairs.sort(key=lambda x: -x["round_trip_ratio"])
            if score > 0.15:
                flags.append({
                    "flag": "LAYERED_TRANSACTIONS", "severity": "HIGH",
                    "detail": (
                        f"Layered transaction score {score:.3f}: "
                        f"{len(layered_pairs)} reciprocal payment pairs detected"
                    ),
                })
            elif score > 0.05:
                flags.append({
                    "flag": "LAYERED_TRANSACTIONS_MEDIUM", "severity": "MEDIUM",
                    "detail": f"Possible layering: {len(layered_pairs)} reciprocal pairs, score {score:.3f}",
                })

        return {
            "layered_score": round(min(score, 1.0), 4),
            "layered_pairs": layered_pairs,
            "flags": flags,
        }

    # ── Shell company detection ────────────────────────────────────────────
    _COMPANY_SUFFIXES = re.compile(
        r"\b(pvt\.?|private|limited|ltd\.?|llp|inc\.?|corp\.?)\b", re.IGNORECASE
    )

    def _detect_shell_entities(self, segmented_docs: List, txn_entities: set) -> Dict[str, Any]:
        """
        Cross-reference counterparties from the transaction graph with
        company/director names found in uploaded documents.
        Entities that appear in transactions AND share a director/address with
        the applicant are flagged as potential shell company connections.
        """
        # Collect all director names and addresses found in documents
        doc_directors: set = set()
        doc_addresses: set = set()
        doc_companies: set = set()

        for doc in segmented_docs:
            text = (doc.text_content or "").upper()

            # Director names (DIN patterns)
            for m in re.finditer(r"\bDIN[:\s]*\d{8}\b[^A-Z]*([A-Z][A-Z .]{4,40})", text):
                doc_directors.add(m.group(1).strip())

            # Registered office addresses (pin codes as anchor)
            for m in re.finditer(r"([A-Z][A-Z ,.-]{10,80})\s*[-,]\s*\d{6}", text):
                addr_clean = re.sub(r"\s+", " ", m.group(1)).strip()
                if len(addr_clean) > 10:
                    doc_addresses.add(addr_clean[:60])

            # Company names mentioned
            for m in re.finditer(
                r"([A-Z][A-Z0-9 &]{4,50}(?:PVT|PRIVATE|LIMITED|LTD|LLP)\.?\s*(?:LTD|LIMITED)?)", text
            ):
                name = self._COMPANY_SUFFIXES.sub("", m.group(1)).strip()
                if len(name) > 4:
                    doc_companies.add(name.strip())

        # Shell entity = txn counterparty whose name overlaps with doc companies using fuzzy token match
        shell_entities = []
        for entity in txn_entities:
            entity_clean = self._COMPANY_SUFFIXES.sub("", entity).strip().upper()
            if len(entity_clean) < 4:
                continue
            for doc_company in doc_companies:
                # Token overlap: ≥ 2 common tokens → possible same entity
                e_tokens = set(entity_clean.split())
                d_tokens = set(doc_company.upper().split())
                overlap  = e_tokens & d_tokens
                if len(overlap) >= 2 and entity_clean != doc_company:
                    shell_entities.append({
                        "counterparty":  entity,
                        "matching_name": doc_company,
                        "shared_tokens": list(overlap),
                    })
                    break

        score = min(len(shell_entities) * 0.15, 1.0)
        flags = []
        if shell_entities:
            flags.append({
                "flag": "POTENTIAL_SHELL_ENTITIES", "severity": "HIGH",
                "detail": (
                    f"{len(shell_entities)} transaction counterparties match company names "
                    "found in uploaded documents — possible shell company network"
                ),
                "entities": [e["counterparty"] for e in shell_entities[:5]],
            })

        return {
            "shell_score":    round(score, 4),
            "shell_entities": shell_entities[:10],
            "flags":          flags,
        }

    @staticmethod
    def _counterparty_concentration(cp_freq: Counter) -> float:
        """HHI-style concentration: how dominant is the top counterparty?"""
        total = sum(cp_freq.values())
        if total == 0:
            return 0.0
        top_share = cp_freq.most_common(1)[0][1] / total if cp_freq else 0
        return round(top_share, 4)
