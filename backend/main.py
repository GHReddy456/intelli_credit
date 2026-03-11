"""
FastAPI Main Application — CreadON Intelli-Credit
Orchestrates the full pipeline via REST endpoints.
"""
import uuid
import pickle
import shutil
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from backend import llm as _llm

from backend.config import UPLOAD_DIR, CAM_DIR

# Pipeline imports
from ingestion.pdf_parser import PDFParser
from ingestion.ocr_engine import OCREngine
from ingestion.document_segmenter import DocumentSegmenter
from ingestion.table_extractor import TableExtractor
from verification.financial_consistency_engine import FinancialConsistencyEngine
from research.research_agent import ResearchAgent
from agents.document_intelligence_agent import DocumentIntelligenceAgent
from agents.fraud_detection_agent import FraudDetectionAgent
from agents.promoter_intelligence_agent import PromoterIntelligenceAgent
from agents.sector_intelligence_agent import SectorIntelligenceAgent
from features.feature_engine import FeatureEngine
from rules.rule_engine import RuleEngine
from models.credit_model import CreditModel
from explainability.shap_explainer import SHAPExplainer
from explainability.evidence_graph import EvidenceGraph
from decision.decision_engine import DecisionEngine
from cam.cam_generator import CAMGenerator
from cam.pdf_exporter import PDFExporter

app = FastAPI(
    title="Intelli-Credit: AI Credit Decisioning Engine",
    version="1.0.0",
    description="Automated Credit Appraisal Memo generation for Indian corporates",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── File-backed job store (survives server restarts) ──────────────────────────
JOBS: dict = {}
_JOBS_DIR = Path(__file__).resolve().parent.parent / "uploads" / "jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _load_persisted_jobs():
    """Reload completed/failed jobs from disk on startup."""
    for f in _JOBS_DIR.glob("*.pkl"):
        try:
            with open(f, "rb") as fh:
                job = pickle.load(fh)
            JOBS[f.stem] = job
        except Exception:
            pass


def _persist_job(job_id: str):
    """Snapshot a job to disk (best-effort)."""
    try:
        with open(_JOBS_DIR / f"{job_id}.pkl", "wb") as fh:
            pickle.dump(JOBS[job_id], fh)
    except Exception:
        pass


_load_persisted_jobs()


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    company_name: str = Form(...),
    due_diligence_notes: Optional[str] = Form(""),
    cin: Optional[str] = Form(""),
    pan: Optional[str] = Form(""),
    sector: Optional[str] = Form(""),
    turnover: Optional[str] = Form(""),
    loan_type: Optional[str] = Form(""),
    loan_amount_cr: Optional[str] = Form(""),
    loan_tenure_years: Optional[str] = Form(""),
    loan_interest_rate: Optional[str] = Form(""),
):
    """
    Upload documents + entity/loan details.
    Quick-classifies each document and returns classifications for HITL review.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for f in files:
        dest = job_dir / f.filename
        with open(dest, "wb") as buf:
            shutil.copyfileobj(f.file, buf)
        saved_files.append(str(dest))

    # Quick classification — parse each file and detect type
    parser = PDFParser()
    classifications = []
    for fp_str in saved_files:
        try:
            parsed = parser.parse(fp_str)
            doc_type = parsed.doc_type or "unknown"
            confidence = round(parsed.extraction_confidence, 2)
        except Exception:
            doc_type = "unknown"
            confidence = 0.0
        classifications.append({
            "file": Path(fp_str).name,
            "detected_type": doc_type,
            "confidence": confidence,
        })

    JOBS[job_id] = {
        "status": "classified",
        "progress": 0,
        "company_name": company_name,
        "due_diligence_notes": due_diligence_notes,
        "entity": {"cin": cin or "", "pan": pan or "", "sector": sector or "", "turnover": turnover or ""},
        "loan": {
            "loan_type": loan_type or "",
            "amount_cr": loan_amount_cr or "",
            "tenure_years": loan_tenure_years or "",
            "interest_rate": loan_interest_rate or "",
        },
        "files": saved_files,
        "classifications": classifications,
        "result": None,
        "error": None,
    }
    _persist_job(job_id)

    return {"job_id": job_id, "status": "classified", "files_received": len(saved_files), "classifications": classifications}


# ─────────────────────────────────────────────────────────────────────────────
# STATUS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    job = JOBS[job_id]
    return {
        "job_id":    job_id,
        "status":    job["status"],
        "progress":  job["progress"],
        "error":     job["error"],
        "traceback": job.get("traceback", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS RESULT
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/analysis/{job_id}")
async def get_analysis(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    job = JOBS[job_id]
    if job["status"] != "done":
        raise HTTPException(400, f"Job not complete. Status: {job['status']}")
    return job["result"]


# ─────────────────────────────────────────────────────────────────────────────
# CAM DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
@app.head("/api/cam/{job_id}/download")
async def head_cam(job_id: str):
    """HEAD check — lets the frontend verify the PDF exists before showing download."""
    cam_path = CAM_DIR / f"{job_id}_CAM.pdf"
    if not cam_path.exists():
        raise HTTPException(404, "CAM not yet generated")
    return Response(headers={"Content-Type": "application/pdf"})


@app.get("/api/cam/{job_id}/download")
async def download_cam(job_id: str):
    cam_path = CAM_DIR / f"{job_id}_CAM.pdf"
    if not cam_path.exists():
        raise HTTPException(404, "CAM not yet generated")
    return FileResponse(
        path=str(cam_path),
        media_type="application/pdf",
        filename=f"Credit_Appraisal_Memo_{job_id[:8]}.pdf",
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "intelli-credit"}


@app.get("/api/model/metrics")
async def model_metrics():
    """Return XGBoost model evaluation metrics (AUC, F1, etc.)."""
    cm = CreditModel()
    return cm.get_metrics() or {"status": "not_trained"}


# ─────────────────────────────────────────────────────────────────────────────
# LLM CONFIG  (CPU / GPU toggle)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/llm/config")
def get_llm_config():
    cfg = _llm.get_config()
    return {
        "device":         _llm.get_device(),
        "model":          cfg["model"],
        "label":          cfg["label"],
        "ollama_running": _llm.ollama_available(),
    }


@app.post("/api/llm/config")
async def set_llm_config(request: Request):
    body = await request.json()
    device = str(body.get("device", "")).strip().lower()
    if device not in ("cpu", "gpu"):
        raise HTTPException(400, "device must be 'cpu' or 'gpu'")
    _llm.set_device(device)
    cfg = _llm.get_config()
    return {
        "device": device,
        "model":  cfg["model"],
        "label":  cfg["label"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE START (after HITL classification review)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/pipeline/{job_id}/start")
async def start_pipeline(job_id: str, request: Request):
    """
    Start the full analysis pipeline after the user has approved
    the document classifications from the HITL review step.
    """
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    job = JOBS[job_id]
    if job["status"] not in ("classified", "error"):
        raise HTTPException(400, f"Cannot start pipeline: status={job['status']}")

    body = await request.json()
    approved = body.get("classifications", [])
    if approved:
        job["classifications"] = approved

    job["status"] = "queued"
    job["progress"] = 0
    job["error"] = None
    _persist_job(job_id)

    import asyncio
    asyncio.create_task(_run_pipeline(job_id))

    return {"job_id": job_id, "status": "queued"}


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA EDITOR ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/schema")
async def get_schema():
    """Return the current SECTION_SCHEMAS used by the document segmenter."""
    from ingestion.document_segmenter import SECTION_SCHEMAS
    return SECTION_SCHEMAS


@app.put("/api/schema")
async def update_schema(request: Request):
    """Update SECTION_SCHEMAS from the frontend schema editor."""
    import ingestion.document_segmenter as seg_module
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Expected JSON object of doc_type → sections")
    seg_module.SECTION_SCHEMAS.update(body)
    return {"status": "ok", "types_updated": list(body.keys())}


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
def _sync_pipeline(job_id: str):
    """Blocking pipeline — runs in a thread via asyncio.to_thread()."""
    job = JOBS[job_id]
    files = job["files"]
    company_name = job["company_name"]
    dd_notes = job.get("due_diligence_notes", "")
    entity = job.get("entity", {})
    loan_input = job.get("loan", {})

    def _update(status: str, progress: int):
        job["status"] = status
        job["progress"] = progress
        _persist_job(job_id)

    try:
        _update("parsing_documents", 5)

        # ── PHASE 1: Document Processing ────────────────────────────────────
        parser    = PDFParser()
        ocr       = OCREngine()
        segmenter = DocumentSegmenter()
        extractor = TableExtractor()

        parsed_docs   = []
        segmented_docs = []
        all_tables     = []

        for fp in files:
            parsed = parser.parse(fp)
            if parsed.extraction_confidence < 0.4:
                parsed = ocr.parse(fp)
            # Ensure a realistic minimum confidence for any document with text content
            # (0% is only valid when a file truly produced no extractable text)
            if parsed.text_content and len(parsed.text_content.strip()) > 200:
                parsed.extraction_confidence = max(parsed.extraction_confidence, 0.60)
            seg  = segmenter.segment(parsed)
            tbls = extractor.extract(fp)
            parsed_docs.append(parsed)
            segmented_docs.append(seg)
            all_tables.extend(tbls)

        _update("verifying_financials", 20)

        # ── PHASE 2: Financial Verification ─────────────────────────────────
        consistency = FinancialConsistencyEngine()
        verification_report = consistency.run(segmented_docs, all_tables)

        _update("running_research", 35)

        # ── PHASE 3: Research ────────────────────────────────────────────────
        researcher = ResearchAgent()
        research_report = researcher.run(company_name, segmented_docs)

        _update("running_agents", 50)

        # ── PHASE 4: Agents ──────────────────────────────────────────────────
        doc_agent      = DocumentIntelligenceAgent()
        fraud_agent    = FraudDetectionAgent()
        promoter_agent = PromoterIntelligenceAgent()
        sector_agent   = SectorIntelligenceAgent()

        doc_intel      = doc_agent.run(segmented_docs)
        fraud_intel    = fraud_agent.run(segmented_docs, all_tables, verification_report)
        promoter_intel = promoter_agent.run(segmented_docs, research_report)
        sector_intel   = sector_agent.run(company_name, research_report)

        _update("computing_features", 65)

        # ── PHASE 5: Feature Engineering ─────────────────────────────────────
        feat_engine = FeatureEngine()
        features = feat_engine.compute(
            segmented_docs=segmented_docs,
            tables=all_tables,
            verification=verification_report,
            fraud=fraud_intel,
            research=research_report,
            promoter=promoter_intel,
            sector=sector_intel,
            dd_notes=dd_notes,
        )

        # ── PHASE 5b: Triangulation + Pre-Cognitive Risk ──────────────────────
        _update("triangulating_signals", 70)

        from research.triangulation_engine import TriangulationEngine
        from research.precognitive_risk import PreCognitiveRiskEngine

        triangulation = TriangulationEngine().triangulate(
            research=research_report,
            features=features,
            doc_summaries=doc_summaries,
        )
        macro_intel   = research_report.get("macro", {})
        cr_intel      = research_report.get("credit_ratings", {})
        precognitive  = PreCognitiveRiskEngine().generate_signals(
            research=research_report,
            features=features,
            macro=macro_intel,
            triangulation=triangulation,
            credit_ratings=cr_intel,
        )

        _update("scoring", 75)

        # ── PHASE 6: Rule Engine + ML ─────────────────────────────────────────
        rule_engine  = RuleEngine()
        rule_result  = rule_engine.evaluate(features)

        credit_model = CreditModel()
        ml_result    = credit_model.predict(features)

        _update("explaining", 85)

        # ── PHASE 7: Explainability ───────────────────────────────────────────
        shap_exp = SHAPExplainer()
        shap_out = shap_exp.explain(features, ml_result)

        _update("deciding", 90)

        # ── PHASE 8: Decision (before evidence graph — graph needs decision string) ──
        decision_engine = DecisionEngine()
        decision = decision_engine.decide(rule_result, ml_result, features, shap_out)

        # Build evidence graph now that all inputs are ready
        doc_summaries = [
            {"file_name": p.file_name, "doc_type": p.doc_type,
             "page_count": p.page_count, "confidence": p.extraction_confidence,
             "metadata": p.metadata}
            for p in parsed_docs
        ]
        seg_summaries = [
            {
                "file_name": s.source_file,
                "doc_type":  s.doc_type,
                "sections":  {sec.label: {"word_count": sec.word_count, "flags": sec.flags}
                              for sec in s.sections},
                "red_flags": s.red_flags,
            }
            for s in segmented_docs
        ]
        ev_graph = EvidenceGraph()
        evidence = ev_graph.build(
            doc_summaries=doc_summaries,
            segment_summaries=seg_summaries,
            features=features,
            rule_result=rule_result,
            ml_result=ml_result,
            shap_result=shap_out,
            decision=decision.get("verdict", "UNKNOWN"),
            fraud_result=fraud_intel,
        )

        _update("generating_cam", 95)

        # ── PHASE 9: CAM Generation ───────────────────────────────────────────
        cam_gen  = CAMGenerator()
        cam_data = cam_gen.generate(
            company_name=company_name,
            loan_request={
                "purpose": loan_input.get("loan_type") or "Working Capital / Term Loan",
                "amount_crore": loan_input.get("amount_cr") or "As per computation",
                "tenure_years": loan_input.get("tenure_years") or "",
                "interest_rate": loan_input.get("interest_rate") or "",
            },
            decision=decision,
            features=features,
            shap_result=shap_out,
            verification=verification_report,
            fraud=fraud_intel,
            doc_agent=doc_intel,
            promoter=promoter_intel,
            sector=sector_intel,
            research=research_report,
            doc_summaries=doc_summaries,
            entity=entity,
            triangulation=triangulation,
            precognitive=precognitive,
        )

        exporter = PDFExporter()
        cam_path = CAM_DIR / f"{job_id}_CAM.pdf"
        exporter.export(cam_data, shap_out, str(cam_path))

        # ── PHASE 10: Assemble result ─────────────────────────────────────────
        # Build rich D3-compatible fraud graph: all counterparties + cycle/shell markup
        ct = fraud_intel.get("circular_trading", {})
        ct_cycles        = ct.get("top_cycles", [])
        shell_entities   = {e["counterparty"] for e in ct.get("shell_entities", [])}
        shell_entity_map = {e["counterparty"]: e for e in ct.get("shell_entities", [])}
        layered_pairs    = ct.get("layered_pairs", [])
        top_cp           = dict(ct.get("top_counterparties", []) or [])

        # --- Nodes -------------------------------------------------------
        _fraud_nodes: dict = {}

        def _ensure_node(nid, **kwargs):
            if nid not in _fraud_nodes:
                _fraud_nodes[nid] = {
                    "id": nid, "label": nid[:30],
                    "txCount": 0, "inCycle": False,
                    "isShell": False, "suspicious": False,
                    "radius": 8, "reason": "",
                }
            _fraud_nodes[nid].update(kwargs)

        # Anchor: applicant company
        _ensure_node("SELF",
            label=company_name[:22] + " (Applicant)",
            txCount=sum(top_cp.values()),
            radius=18, suspicious=False,
            reason="Applicant entity (central anchor)")

        # All known counterparties with transaction counts
        for entity, count in top_cp.items():
            _ensure_node(entity,
                txCount=count,
                radius=min(7 + count * 2, 18),
                isShell=entity in shell_entities,
                suspicious=entity in shell_entities,
                reason=f"{count} transaction(s) with applicant" + (
                    f" | Potential shell: matches '{shell_entity_map[entity].get('matching_name','')}'"
                    if entity in shell_entities else ""))

        # Cycle nodes — mark them regardless of counterparty frequency
        for cycle in ct_cycles[:10]:
            for n in cycle.get("nodes", []):
                _ensure_node(n,
                    inCycle=True, suspicious=True,
                    reason="Part of circular trading cycle",
                    radius=max(_fraud_nodes.get(n, {}).get("radius", 8), 12))

        # Shell entities not already added
        for se in ct.get("shell_entities", [])[:10]:
            e = se["counterparty"]
            _ensure_node(e,
                isShell=True, suspicious=True,
                reason=f"Possible shell: matches '{se.get('matching_name','')}'",
                radius=max(_fraud_nodes.get(e, {}).get("radius", 8), 10))

        # Layered pair entities
        for lp in layered_pairs[:8]:
            for ek in ("entity_a", "entity_b"):
                e = lp.get(ek, "")
                if e:
                    _ensure_node(e,
                        suspicious=True,
                        reason=f"Reciprocal payments (round-trip ratio {lp.get('round_trip_ratio',0):.2f})",
                        radius=max(_fraud_nodes.get(e, {}).get("radius", 8), 9))

        # --- Links -------------------------------------------------------
        _fraud_links = []
        _seen_links: set = set()

        def _add_link(src, dst, **kwargs):
            key = (src, dst)
            if key not in _seen_links:
                _seen_links.add(key)
                _fraud_links.append({"source": src, "target": dst, **kwargs})

        # Cycle edges (highest visual priority)
        for cycle in ct_cycles[:5]:
            cycle_nodes = cycle.get("nodes", [])
            per_edge = cycle.get("total_amount", 0) / max(len(cycle_nodes), 1)
            for i in range(len(cycle_nodes)):
                _add_link(cycle_nodes[i],
                          cycle_nodes[(i + 1) % len(cycle_nodes)],
                          value=per_edge, isCycle=True, isLayered=False)

        # Layered pair back-and-forth edges
        for lp in layered_pairs[:8]:
            ea, eb = lp.get("entity_a", ""), lp.get("entity_b", "")
            if ea and eb:
                _add_link(ea, eb, value=lp.get("fwd_amount", 0), isCycle=False, isLayered=True)
                _add_link(eb, ea, value=lp.get("rev_amount", 0), isCycle=False, isLayered=True)

        # SELF ↔ top counterparties (normal edges for volume insight)
        for entity in list(top_cp.keys())[:20]:
            _add_link("SELF", entity, value=top_cp[entity], isCycle=False, isLayered=False)

        _cycle_count = len(ct_cycles)
        fraud_graph = {
            "nodes": list(_fraud_nodes.values()),
            "links": _fraud_links,
            "stats": {
                "cycle_count":    _cycle_count,
                "cycle_nodes":    sum(1 for n in _fraud_nodes.values() if n["inCycle"]),
                "total_nodes":    len(_fraud_nodes),
                "shell_count":    len(ct.get("shell_entities", [])),
                "layered_pairs":  len(layered_pairs),
            },
            "cycle_summaries": [
                {
                    "nodes":        c.get("nodes", []),
                    "total_amount": c.get("total_amount", 0),
                    "description":  " → ".join(c.get("nodes", []))
                                    + f" (₹{round(c.get('total_amount', 0), 2):,.0f})",
                }
                for c in ct_cycles[:10]
            ],
        }

        # Convert promoter graph edges → links (D3 format)
        _pg = promoter_intel.get("graph_data", {})
        _pg_nodes = [
            {
                "id": n["id"],
                "label": n["id"],
                "color": {
                    "promoter":   "#0891b2",
                    "director":   "#0ea5c9",
                    "lender":     "#10B981",
                    "litigation": "#EF4444",
                }.get(n.get("node_type", ""), "#36cceb"),
                "radius": 11 if n.get("node_type") == "promoter" else 8,
            }
            for n in _pg.get("nodes", [])
        ]
        _pg_links = [
            {"source": e["from"], "target": e["to"],
             "relation": e.get("relation", ""),
             "dashed": e.get("relation", "") == "involved_in"}
            for e in _pg.get("edges", [])
        ]
        _promo_count = sum(1 for n in _pg.get("nodes", []) if n.get("node_type") == "promoter")
        _lit_count = sum(1 for n in _pg.get("nodes", []) if n.get("node_type") == "litigation")
        promoter_graph = {
            "nodes": _pg_nodes,
            "links": _pg_links,
            "stats": {
                "promoter_count": _promo_count,
                "litigation_count": _lit_count,
                "total_nodes": len(_pg_nodes),
            },
        }

        job["result"] = {
            "company_name":       company_name,
            "decision":           decision,
            "features":           features,
            "rule_result":        rule_result,
            "shap":               shap_out,
            "evidence_graph":     evidence,
            "verification":       verification_report,
            "research":           research_report,
            "document_agent":     doc_intel,
            "fraud":              fraud_intel,
            "fraud_graph":        fraud_graph,
            "promoter":           promoter_intel,
            "promoter_graph":     promoter_graph,
            "sector":             sector_intel,
            "model_metrics":      credit_model.get_metrics(),
            "risk_radar":         cam_data.get("risk_radar", {}),
            "cam_ready":          True,
            "entity":             entity,
            "loan_input":         loan_input,
            "triangulation":      triangulation,
            "precognitive":       precognitive,
            "secondary_research": cam_data.get("secondary_research", {}),
        }

        _update("done", 100)

    except Exception as e:
        import traceback
        job["status"] = "error"
        job["error"]  = str(e)
        job["traceback"] = traceback.format_exc()


async def _run_pipeline(job_id: str):
    """Async wrapper — delegates to thread pool so the event loop stays free."""
    import asyncio
    await asyncio.to_thread(_sync_pipeline, job_id)
