"""
Transaction Graph Builder
Constructs a NetworkX directed graph from bank statement transactions.
Nodes = entities (account/GSTIN/company name). Edges = transactions (weighted by amount, dated).

Improvements:
- Uses ingestion.numeric_normalizer for robust amount parsing (handles Cr/Lakh, Indian commas)
- Richer narration parser: NEFT/RTGS/IMPS, UPI, ACH, cheque, fund-transfer patterns
- Exposes counterparty frequency map for layered-transaction detection
- Exposes all_entities set for shell-company cross-matching
"""
import re
import networkx as nx
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from ingestion.numeric_normalizer import parse_amount_robust, normalize_amounts


class TransactionGraph:
    """
    Builds the transaction graph used by CircularTradingDetector.
    Also exposes graph-level statistics and counterparty analytics for risk scoring.
    """

    def build(self, segmented_docs: List, tables: List[Dict]) -> nx.DiGraph:
        G = nx.DiGraph()
        transactions = self._extract_transactions(segmented_docs, tables)

        for txn in transactions:
            src  = txn.get("from_entity", "UNKNOWN")
            dst  = txn.get("to_entity", "UNKNOWN")
            amt  = txn.get("amount", 0) or 0
            date = txn.get("date", "")
            narr = txn.get("narration", "")

            # Both ends unresolved — still add to graph using APPLICANT→UNKNOWN
            # so that repeated same-counterparty patterns are captured
            if src == dst:
                continue
            # Accept edges where at least one end is resolved (or use APPLICANT as anchor)
            if src == "UNKNOWN" and dst == "UNKNOWN":
                continue

            if not G.has_edge(src, dst):
                G.add_edge(src, dst, transactions=[], total_amount=0, dates=[])
            G[src][dst]["transactions"].append({"amount": amt, "date": date, "narration": narr})
            G[src][dst]["total_amount"] += amt
            if date:
                G[src][dst]["dates"].append(date)

        logger.info(f"[TxnGraph] Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G

    def stats(self, G: nx.DiGraph) -> Dict[str, Any]:
        return {
            "node_count":  G.number_of_nodes(),
            "edge_count":  G.number_of_edges(),
            "density":     round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0,
            "top_nodes":   sorted(dict(G.degree()).items(), key=lambda x: -x[1])[:10],
        }

    def counterparty_frequency(self, segmented_docs: List, tables: List[Dict]) -> Counter:
        """Return a Counter of {entity_name: transaction_count} across all docs."""
        txns = self._extract_transactions(segmented_docs, tables)
        ctr: Counter = Counter()
        for txn in txns:
            for field in ("from_entity", "to_entity"):
                e = txn.get(field, "UNKNOWN")
                if e not in ("UNKNOWN", "SELF"):
                    ctr[e] += 1
        return ctr

    def all_entities(self, segmented_docs: List, tables: List[Dict]) -> set:
        """Return the set of all normalised counterparty names found."""
        txns = self._extract_transactions(segmented_docs, tables)
        entities = set()
        for txn in txns:
            for field in ("from_entity", "to_entity"):
                e = txn.get(field, "UNKNOWN")
                if e not in ("UNKNOWN", "SELF"):
                    entities.add(e)
        return entities

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
        txn: Dict = {}
        for key, val in row.items():
            kl = key.lower()
            if "date" in kl:
                txn["date"] = val
            elif "debit" in kl and "amount" not in txn:
                v = self._to_float(val)
                if v and v > 0:
                    txn["amount"] = v
                    txn["direction"] = "debit"
            elif "credit" in kl and "amount" not in txn and "debit" not in kl:
                v = self._to_float(val)
                if v and v > 0:
                    txn["amount"] = v
                    txn["direction"] = "credit"
            elif any(x in kl for x in ["narration", "description", "particulars", "remarks"]):
                txn["narration"] = val

        if "amount" not in txn:
            return None

        narr = txn.get("narration", "")
        txn["from_entity"], txn["to_entity"] = self._extract_entities(narr, txn.get("direction", ""))
        return txn

    def _parse_text_transactions(self, text: str) -> List[Dict]:
        """Parse transactions from unstructured bank statement text.
        Handles multiple common Indian bank statement formats.
        """
        txns = []

        # Format 1: DD/MM/YYYY  <narration>  debit  credit  balance
        # The balance column is optional (some statements omit it)
        pattern1 = re.compile(
            r"(?P<date>\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s+"
            r"(?P<narration>.{5,120}?)\s{1,}"
            r"(?P<debit>[\d,]+\.\d{2})?\s*"
            r"(?P<credit>[\d,]+\.\d{2})?\s*"
            r"(?P<balance>[\d,]+(?:\.\d{2})?)?",
            re.MULTILINE,
        )
        # Format 2: lines like "01-Apr-2023  NEFT TO ACME LTD  500000.00  Cr"
        pattern2 = re.compile(
            r"(?P<date>\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{2,4})\s+"
            r"(?P<narration>.{5,120}?)\s+"
            r"(?P<amount>[\d,]+\.\d{2})\s*"
            r"(?P<dr_cr>Dr\.?|Cr\.?|DR|CR)",
            re.IGNORECASE | re.MULTILINE,
        )

        seen = set()

        for m in pattern2.finditer(text):
            narr      = m.group("narration").strip()
            amount    = self._to_float(m.group("amount") or "")
            if not amount or amount <= 0:
                continue
            dr_cr     = m.group("dr_cr").upper()
            direction = "debit" if dr_cr.startswith("D") else "credit"
            key       = (m.group("date"), narr[:20], direction)
            if key in seen:
                continue
            seen.add(key)
            from_e, to_e = self._extract_entities(narr, direction)
            txns.append({
                "date": m.group("date"), "narration": narr,
                "amount": amount, "direction": direction,
                "from_entity": from_e, "to_entity": to_e,
            })

        if not txns:
            for m in pattern1.finditer(text):
                debit  = self._to_float(m.group("debit") or "")
                credit = self._to_float(m.group("credit") or "")
                if not (debit or credit):
                    continue
                narr      = m.group("narration").strip()
                if len(narr) < 4:
                    continue
                direction = "debit" if debit else "credit"
                amount    = debit or credit
                key       = (m.group("date"), narr[:20], direction)
                if key in seen:
                    continue
                seen.add(key)
                from_e, to_e = self._extract_entities(narr, direction)
                txns.append({
                    "date": m.group("date"), "narration": narr,
                    "amount": amount, "direction": direction,
                    "from_entity": from_e, "to_entity": to_e,
                })

        return txns

    # ── Entity extraction ─────────────────────────────────────────────────
    # Ordered list of (pattern, name_group_index) for narration parsing
    _NARR_PATTERNS = [
        # NEFT/RTGS/IMPS: "NEFT CR-HDFC0001234-ACME PVT LTD-REF..." or "NEFT/CR/IFSC/NAME"
        (re.compile(r"(?:NEFT|RTGS|IMPS)[/ -]+(?:CR|DR)[/ -]+[A-Z0-9]{3,15}[/ -]+([A-Z0-9 &./()PVTLTD-]{4,50})", re.IGNORECASE), 1),
        # UPI: "UPI/DR/REF/ACME TRADERS/REMARKS" or "UPI-ACME@upi"
        (re.compile(r"UPI[/ -]+(?:CR|DR)[/ -]+\d+[/ -]+([A-Z0-9 &./()-]{4,50})", re.IGNORECASE), 1),
        (re.compile(r"UPI[/ -]+([A-Z0-9 &./-]{4,40})@[A-Z]{2,10}", re.IGNORECASE), 1),
        # ACH/ECS/NACH: "ACH DR ACME FINANCE LTD"
        (re.compile(r"(?:ACH|ECS|NACH)[/ -]+(?:CR|DR)[/ -]+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # "BY TRANSFER TO ACME LTD" / "TRANSFER TO"
        (re.compile(r"(?:BY TRANSFER TO|TO TRANSFER|TRANSFER TO)\s+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # "FROM ACME" / "BY ACME"
        (re.compile(r"\b(?:FROM|BY)\s+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # Cheque: "CHQ NO 001234 ACME INDUSTRIES"
        (re.compile(r"CHQ(?:UE)? (?:NO\.? ?\d+)?\s+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # "PAYMENT TO ACME" / "TO ACME CORP"
        (re.compile(r"(?:PAYMENT |PAID )?TO\s+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # IMPS/INB format: "INB ACME INDUSTRIES 1234"
        (re.compile(r"INB\s+([A-Z][A-Z0-9 &./()-]{3,50})", re.IGNORECASE), 1),
        # Company-name heuristic: words containing Ltd/Pvt/LLP → strong entity signal
        (re.compile(r"([A-Z][A-Z0-9 &.]{3,50}(?:LTD|PVT|LLP|LIMITED|PRIVATE|CORP|INC)\.?)\b", re.IGNORECASE), 1),
    ]

    # Account-number extraction — used as fallback entity when company name not found
    _ACCT_RE = re.compile(r"\b(\d{9,18})\b")
    # IFSC code extraction
    _IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")

    def _extract_entities(self, narration: str, direction: str) -> Tuple[str, str]:
        """Extract and normalise counterparty name from NEFT/RTGS/UPI/etc narration."""
        for pattern, grp in self._NARR_PATTERNS:
            m = pattern.search(narration)
            if m:
                entity = self._normalise_entity(m.group(grp))
                if entity and len(entity) >= 3:
                    return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        # Fallback 1: Use account number as entity identifier
        acc_m = self._ACCT_RE.search(narration)
        if acc_m:
            entity = f"ACCT_{acc_m.group(1)}"
            return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        # Fallback 2: Use IFSC as entity identifier (bank branch = approximate entity)
        ifsc_m = self._IFSC_RE.search(narration)
        if ifsc_m:
            entity = f"BANK_{ifsc_m.group(1)[:4]}"
            return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        # Fallback 3: Extract any 3+ word ALL-CAPS sequence (common in bank statements)
        caps_m = re.search(r"([A-Z]{3,}(?:\s+[A-Z]{2,}){1,5})", narration)
        if caps_m:
            entity = self._normalise_entity(caps_m.group(1))
            if entity and len(entity) >= 3:
                return ("SELF", entity) if direction == "debit" else (entity, "SELF")

        return ("SELF", "UNKNOWN")

    @staticmethod
    def _normalise_entity(raw: str) -> str:
        """Strip noise, uppercase, collapse whitespace."""
        # Remove trailing reference codes like -REF123 or /12345
        cleaned = re.sub(r"[/\-]\s*\d{4,}.*$", "", raw)
        # Remove leading/trailing junk
        cleaned = re.sub(r"[^A-Z0-9 &./()-]", "", cleaned.upper()).strip()
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned if len(cleaned) >= 3 else ""

    def _to_float(self, s: str) -> Optional[float]:
        """Use central normalizer; fall back to plain strip."""
        val = parse_amount_robust(str(s))
        if val is not None:
            return val
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
