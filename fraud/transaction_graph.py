"""
Transaction Graph Builder
Constructs a NetworkX directed graph from bank statement transactions.
Nodes = entities (account/GSTIN). Edges = transactions (weighted by amount, dated).
"""
import re
import networkx as nx
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class TransactionGraph:
    """
    Builds the transaction graph used by CircularTradingDetector.
    Also exposes graph-level statistics for risk scoring.
    """

    def build(self, segmented_docs: List, tables: List[Dict]) -> nx.DiGraph:
        G = nx.DiGraph()
        transactions = self._extract_transactions(segmented_docs, tables)

        for txn in transactions:
            src  = txn.get("from_entity", "UNKNOWN")
            dst  = txn.get("to_entity", "UNKNOWN")
            amt  = txn.get("amount", 0)
            date = txn.get("date", "")
            narr = txn.get("narration", "")

            if not G.has_edge(src, dst):
                G.add_edge(src, dst, transactions=[], total_amount=0)
            G[src][dst]["transactions"].append({
                "amount": amt, "date": date, "narration": narr
            })
            G[src][dst]["total_amount"] += amt

        logger.info(f"[TxnGraph] Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def stats(self, G: nx.DiGraph) -> Dict[str, Any]:
        return {
            "node_count":  G.number_of_nodes(),
            "edge_count":  G.number_of_edges(),
            "density":     round(nx.density(G), 4),
            "top_nodes":   sorted(dict(G.degree()).items(), key=lambda x: -x[1])[:10],
        }

    # ── Transaction extraction ────────────────────────────────────────────
    def _extract_transactions(self, docs: List, tables: List[Dict]) -> List[Dict]:
        txns = []

        # From bank statement tables
        for tbl in tables:
            if not self._is_bank_table(tbl):
                continue
            for row in tbl.get("rows", []):
                txn = self._parse_row(row)
                if txn:
                    txns.append(txn)

        # From bank statement text (narration parser)
        for doc in docs:
            if doc.doc_type != "bank_statement":
                continue
            txns.extend(self._parse_text_transactions(doc.text_content))

        logger.info(f"[TxnGraph] Extracted {len(txns)} transactions")
        return txns

    def _is_bank_table(self, tbl: Dict) -> bool:
        headers = " ".join(tbl.get("headers", [])).lower()
        indicators = ["debit", "credit", "balance", "narration", "date"]
        return sum(ind in headers for ind in indicators) >= 3

    def _parse_row(self, row: Dict) -> Optional[Dict]:
        txn = {}
        for key, val in row.items():
            kl = key.lower()
            if "date" in kl:
                txn["date"] = val
            elif "debit" in kl:
                v = self._to_float(val)
                if v:
                    txn["amount"] = v
                    txn["direction"] = "debit"
            elif "credit" in kl and "amount" not in txn:
                v = self._to_float(val)
                if v:
                    txn["amount"] = v
                    txn["direction"] = "credit"
            elif any(x in kl for x in ["narration", "description", "particulars", "remarks"]):
                txn["narration"] = val

        if "amount" not in txn:
            return None

        # Try to extract entity from narration
        narr = txn.get("narration", "")
        txn["from_entity"], txn["to_entity"] = self._extract_entities(narr, txn.get("direction", ""))
        return txn

    def _parse_text_transactions(self, text: str) -> List[Dict]:
        """Parse transactions from unstructured bank statement text."""
        txns = []
        pattern = re.compile(
            r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+"
            r"(?P<narration>.{10,80}?)\s+"
            r"(?P<debit>[\d,]+\.\d{2})?\s*"
            r"(?P<credit>[\d,]+\.\d{2})?\s+"
            r"(?P<balance>[\d,]+\.\d{2})",
            re.MULTILINE,
        )
        for m in pattern.finditer(text):
            debit  = self._to_float(m.group("debit") or "")
            credit = self._to_float(m.group("credit") or "")
            if not (debit or credit):
                continue
            narr = m.group("narration").strip()
            direction = "debit" if debit else "credit"
            amount    = debit or credit
            from_e, to_e = self._extract_entities(narr, direction)
            txns.append({
                "date":        m.group("date"),
                "narration":   narr,
                "amount":      amount,
                "direction":   direction,
                "from_entity": from_e,
                "to_entity":   to_e,
            })
        return txns

    def _extract_entities(self, narration: str, direction: str):
        """Extract sender/receiver from NEFT/RTGS/IMPS narration."""
        # NEFT narration format: "NEFT CR/DR-IFSC-NAME-REF"
        m = re.search(r"(?:NEFT|RTGS|IMPS)[- ]+(?:CR|DR)[- ]+([A-Z0-9]+)[- ]+([^-]+)", narration, re.IGNORECASE)
        if m:
            entity = m.group(2).strip()
            return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        # Cheque: /CHQNO/...
        m2 = re.search(r"BY TRANSFER|TO TRANSFER|(?:FROM|TO)\s+([A-Z &.]{4,40})", narration, re.IGNORECASE)
        if m2:
            entity = m2.group(1).strip() if m2.lastindex else "UNKNOWN"
            return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        return ("SELF", "UNKNOWN")

    def _to_float(self, s: str) -> Optional[float]:
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
