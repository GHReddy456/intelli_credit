import React, { useState, useEffect } from "react";

export default function CAMViewer({ jobId }) {
  const [showViewer, setShowViewer] = useState(false);
  const [pdfOk,      setPdfOk]      = useState(null); // null=checking true/false

  // Relative URL for HEAD check (goes through CRA proxy)
  const pdfUrl    = jobId ? `/api/cam/${jobId}/download` : null;
  // Absolute URL for download and <object> — bypasses any proxy ambiguity
  const pdfAbsUrl = jobId ? `http://localhost:8000/api/cam/${jobId}/download` : null;

  useEffect(() => {
    if (!pdfUrl) return;
    setPdfOk(null);
    setShowViewer(false);
    fetch(pdfUrl, { method: "HEAD" })
      .then(r => setPdfOk(r.ok))
      .catch(() => setPdfOk(false));
  }, [pdfUrl]);

  if (!jobId) {
    return (
      <div className="glass" style={{ borderRadius: 20, padding: "60px 40px", textAlign: "center", color: "rgba(255,255,255,0.45)" }}>
        <div style={{ fontSize:58, marginBottom: 16 }}>📋</div>
        <p style={{ fontSize:19, fontWeight: 600, marginBottom: 8 }}>No analysis loaded</p>
        <p style={{ fontSize:19 }}>Upload documents and run the pipeline first.</p>
      </div>
    );
  }

  const checking = pdfOk === null;
  const ready    = pdfOk === true;

  return (
    <div className="fade-in-up">

      {/* ── Hero download card ─────────────────────────── */}
      <div className="glass" style={{
        borderRadius: 24, padding: "36px 40px", marginBottom: 20,
        textAlign: "center",
        background: "rgba(26,14,7,0.92)",
        border: "2px solid rgba(236,91,19,.2)",
      }}>
        <div style={{ fontSize:64, marginBottom: 12 }}>📋</div>
        <h2 style={{ fontSize:22, fontWeight: 900, color: "#f1f5f9", marginBottom: 6 }}>
          Credit Appraisal Memorandum
        </h2>
        <p style={{ fontSize:19, color: "rgba(255,255,255,0.45)", marginBottom: 20 }}>
          AI-generated report — Five Cs · Financial Ratios · SHAP Attribution · Fraud Score · Final Decision
        </p>

        {/* Section badges */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center", marginBottom: 28 }}>
          {[["📊","Five Cs Analysis"],["📈","SHAP Waterfall"],["🔒","Fraud Score"],["👤","Promoter Profile"],["⚖️","Final Verdict"],["🏦","Sector Analysis"],["📉","Financial Ratios"],["🔍","Risk Narrative"]].map(([icon,label]) => (
            <span key={label} style={{ padding: "5px 14px", borderRadius: 20, background: "rgba(236,91,19,.12)", color: "#ec5b13", fontSize:17, fontWeight: 600 }}>
              {icon} {label}
            </span>
          ))}
        </div>

        {/* Status */}
        <div style={{ marginBottom: 24 }}>
          {checking && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 20px", borderRadius: 20, background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.55)", fontSize:19 }}>
              <div style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid #CBD5E1", borderTop: "2px solid #36cceb", animation: "spin 0.8s linear infinite" }} />
              Checking report availability…
            </div>
          )}
          {pdfOk === false && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 20px", borderRadius: 20, background: "rgba(239,68,68,.1)", color: "#EF4444", fontSize:19, fontWeight: 600 }}>
              ✗ PDF not ready — run the pipeline first
            </div>
          )}
          {ready && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 20px", borderRadius: 20, background: "rgba(16,185,129,.1)", color: "#059669", fontSize:19, fontWeight: 600 }}>
              ✓ PDF Ready · {jobId.slice(0, 8).toUpperCase()}
            </div>
          )}
        </div>

        {/* ── Single primary download button ─────────── */}
        {ready ? (
          <button
            onClick={() => window.open(pdfAbsUrl, "_blank", "noopener,noreferrer")}
            style={{
              display: "inline-flex", alignItems: "center", gap: 12,
              padding: "16px 40px", borderRadius: 16,
              background: "linear-gradient(135deg,#059669,#10B981)",
              color: "#fff", fontWeight: 800, fontSize:19, border: "none", cursor: "pointer",
              boxShadow: "0 8px 28px rgba(16,185,129,.40)",
              transition: "box-shadow .2s, transform .2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 12px 36px rgba(16,185,129,.55)"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)";    e.currentTarget.style.boxShadow = "0 8px 28px rgba(16,185,129,.40)"; }}
          >
            ⬇ Download CAM Report (PDF)
          </button>
        ) : (
          <button disabled style={{ display: "inline-flex", alignItems: "center", gap: 12, padding: "16px 40px", borderRadius: 16, background: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.3)", fontWeight: 800, fontSize:19, border: "none", cursor: "not-allowed" }}>
            ⬇ Download CAM Report (PDF)
          </button>
        )}

        {/* Secondary: view inline link */}
        {ready && (
          <div style={{ marginTop: 14 }}>
            <button
              onClick={() => setShowViewer(!showViewer)}
              style={{ background: "none", border: "none", color: "#ec5b13", fontSize:15, cursor: "pointer", textDecoration: "underline", fontWeight: 600 }}>
              {showViewer ? "▲ Hide inline viewer" : "▼ Preview inline"}
            </button>
          </div>
        )}
      </div>

      {/* ── Inline PDF viewer (secondary) ─────────────── */}
      {showViewer && ready && (
        <div className="glass" style={{ borderRadius: 20, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderBottom: "1px solid rgba(54,204,235,.15)" }}>
            <span style={{ fontSize:15, fontWeight: 600, color: "#ec5b13" }}>📋 CAM · {jobId.slice(0, 8).toUpperCase()}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => window.open(pdfAbsUrl, "_blank", "noopener,noreferrer")} style={{ background: "rgba(236,91,19,.12)", border: "none", borderRadius: 8, padding: "4px 10px", cursor: "pointer", fontSize:17, color: "#ec5b13", fontWeight: 600 }}>
                ↗ Full screen
              </button>
              <button onClick={() => setShowViewer(false)} style={{ background: "rgba(239,68,68,.1)", border: "none", borderRadius: 8, padding: "4px 10px", cursor: "pointer", fontSize:15, color: "#EF4444", fontWeight: 700 }}>
                ✕
              </button>
            </div>
          </div>
          <object data={pdfAbsUrl} type="application/pdf" style={{ width: "100%", height: "78vh", display: "block", border: "none" }}>
            <div style={{ padding: 40, textAlign: "center" }}>
              <p style={{ color: "#475569", marginBottom: 12 }}>Your browser cannot display the PDF inline.</p>
              <a href={pdfAbsUrl} target="_blank" rel="noopener noreferrer" style={{ padding: "10px 20px", borderRadius: 10, background: "#10B981", color: "#fff", textDecoration: "none", fontWeight: 600 }}>Download PDF</a>
            </div>
          </object>
        </div>
      )}
    </div>
  );
}


