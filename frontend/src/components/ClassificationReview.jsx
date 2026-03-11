import React, { useState } from "react";

/* ── Material icon helper ───────────────────────────── */
function Icon({ n, style = {} }) {
  return <span className="material-symbols-outlined" style={{ userSelect:"none", ...style }}>{n}</span>;
}

const DOC_TYPE_OPTIONS = [
  { value: "annual_report",        label: "Annual Report" },
  { value: "alm",                  label: "ALM Statement" },
  { value: "shareholding_pattern", label: "Shareholding Pattern" },
  { value: "borrowing_profile",    label: "Borrowing Profile" },
  { value: "portfolio_performance",label: "Portfolio Performance" },
  { value: "gst",                  label: "GSTR-3B" },
  { value: "bank_statement",       label: "Bank Statement" },
  { value: "itr",                  label: "ITR-6" },
  { value: "legal",                label: "Legal Docs" },
  { value: "sanction_letter",      label: "Sanction Letter" },
  { value: "other",                label: "Other" },
];

const TYPE_COLORS = {
  annual_report:        "#a855f7",
  alm:                  "#0891b2",
  shareholding_pattern: "#059669",
  borrowing_profile:    "#D97706",
  portfolio_performance:"#7C3AED",
  gst:                  "#60a5fa",
  bank_statement:       "#4ade80",
  itr:                  "#fb923c",
  legal:                "#f87171",
  sanction_letter:      "#ec5b13",
  other:                "#94a3b8",
};

export default function ClassificationReview({
  classifications = [],
  onApprove,
  onBack,
  theme = "dark",
  companyName = "",
}) {
  const isDark = theme === "dark";
  const [overrides, setOverrides] = useState({});
  const [approvedSet, setApprovedSet] = useState(new Set());

  const T = {
    bg:      isDark ? "linear-gradient(100deg, #0a0604 0%, #110c07 35%, #1a0f08 55%, #2a1206 75%, #1a0d05 100%)" : "#fdf8f2",
    color:   isDark ? "#f1f5f9" : "#1a0e06",
    muted:   isDark ? "#94a3b8" : "#64748b",
    inputBg: isDark ? "rgba(34,22,16,0.6)" : "#ffffff",
    inputBd: isDark ? "rgba(236,91,19,0.25)" : "rgba(236,91,19,0.35)",
    cardBg:  isDark ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.85)",
    cardBd:  isDark ? "rgba(255,255,255,0.1)"  : "rgba(236,91,19,0.18)",
  };
  const glass = isDark
    ? { background:"rgba(34,22,16,0.7)", backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.2)" }
    : { background:"rgba(255,255,255,0.88)", backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.22)" };

  const handleTypeChange = (idx, newType) => {
    setOverrides(prev => ({ ...prev, [idx]: newType }));
  };

  const toggleApprove = (idx) => {
    setApprovedSet(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const approveAll = () => {
    setApprovedSet(new Set(classifications.map((_, i) => i)));
  };

  const allApproved = classifications.length > 0 && approvedSet.size === classifications.length;

  const handleConfirm = () => {
    const finalClassifications = classifications.map((c, i) => ({
      ...c,
      doc_type: overrides[i] || c.doc_type,
      user_approved: approvedSet.has(i),
    }));
    onApprove(finalClassifications);
  };

  return (
    <div style={{ minHeight:"100vh", background:T.bg, fontFamily:"'Public Sans',sans-serif", color:T.color }}>
      {/* Header */}
      <div style={{ textAlign:"center", padding:"48px 24px 24px" }}>
        <div style={{ marginBottom:12 }}>
          <span style={{
            display:"inline-flex", alignItems:"center", gap:6,
            background:"rgba(16,185,129,0.15)", border:"1px solid rgba(16,185,129,0.4)",
            borderRadius:20, padding:"6px 16px",
            fontSize:11, fontWeight:800, color:"#10B981", letterSpacing:"0.1em",
          }}>
            <Icon n="fact_check" style={{ fontSize:14 }} />
            HUMAN-IN-THE-LOOP REVIEW
          </span>
        </div>
        <h1 style={{ fontSize:40, fontWeight:900, letterSpacing:"-1px", margin:"0 0 12px" }}>
          Document Classification Review
        </h1>
        <p style={{ fontSize:15, color:T.muted, maxWidth:600, margin:"0 auto", lineHeight:1.7 }}>
          Our AI has auto-classified your uploaded documents. Review, edit types if needed,
          and approve before starting the full analysis pipeline.
        </p>
        {companyName && (
          <div style={{ marginTop:12, fontSize:13, color:"#ec5b13", fontWeight:700 }}>
            Entity: {companyName}
          </div>
        )}
      </div>

      {/* Stats bar */}
      <div style={{ maxWidth:800, margin:"0 auto 24px", padding:"0 24px" }}>
        <div style={{ ...glass, borderRadius:16, padding:"16px 24px", display:"flex", justifyContent:"space-around", gap:16 }}>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:24, fontWeight:900, color:"#ec5b13" }}>{classifications.length}</div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.08em" }}>Documents</div>
          </div>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:24, fontWeight:900, color:"#10B981" }}>{approvedSet.size}</div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.08em" }}>Approved</div>
          </div>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:24, fontWeight:900, color:"#F59E0B" }}>{Object.keys(overrides).length}</div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.08em" }}>Overridden</div>
          </div>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontSize:24, fontWeight:900, color: allApproved ? "#10B981" : "#64748b" }}>{allApproved ? "✓" : "—"}</div>
            <div style={{ fontSize:11, color:T.muted, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.08em" }}>Ready</div>
          </div>
        </div>
      </div>

      {/* Classification cards */}
      <div style={{ maxWidth:800, margin:"0 auto 24px", padding:"0 24px" }}>
        {classifications.map((cls, idx) => {
          const currentType = overrides[idx] || cls.doc_type;
          const color = TYPE_COLORS[currentType] || "#94a3b8";
          const isApproved = approvedSet.has(idx);
          const confidence = cls.confidence || 0;
          const isOverridden = !!overrides[idx];

          return (
            <div key={idx} style={{
              ...glass,
              borderRadius:16, padding:"20px 24px", marginBottom:12,
              border: isApproved
                ? "1px solid rgba(16,185,129,0.4)"
                : `1px solid ${T.cardBd}`,
              transition:"all .25s",
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:16, flexWrap:"wrap" }}>
                {/* File icon + name */}
                <div style={{ display:"flex", alignItems:"center", gap:10, flex:"1 1 200px", minWidth:200 }}>
                  <div style={{
                    width:42, height:42, borderRadius:10,
                    background:`${color}20`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                  }}>
                    <Icon n="description" style={{ color, fontSize:22 }} />
                  </div>
                  <div>
                    <div style={{ fontSize:13, fontWeight:700, color:T.color, wordBreak:"break-all" }}>
                      {cls.file_name || `Document ${idx + 1}`}
                    </div>
                    <div style={{ fontSize:11, color:T.muted }}>
                      {cls.page_count || 0} pages
                    </div>
                  </div>
                </div>

                {/* Type dropdown */}
                <div style={{ flex:"0 0 auto" }}>
                  <select
                    value={currentType}
                    onChange={e => handleTypeChange(idx, e.target.value)}
                    style={{
                      padding:"8px 12px", borderRadius:8,
                      background:T.inputBg, color:T.color,
                      border:`1px solid ${isOverridden ? "#F59E0B" : T.inputBd}`,
                      fontSize:12, fontWeight:600, fontFamily:"'Public Sans',sans-serif",
                      cursor:"pointer", outline:"none",
                    }}
                  >
                    {DOC_TYPE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {isOverridden && (
                    <span style={{ fontSize:10, color:"#F59E0B", marginLeft:6, fontWeight:700 }}>EDITED</span>
                  )}
                </div>

                {/* Confidence bar */}
                <div style={{ flex:"0 0 120px" }}>
                  <div style={{ fontSize:10, color:T.muted, marginBottom:4, fontWeight:600 }}>
                    Confidence: {(confidence * 100).toFixed(0)}%
                  </div>
                  <div style={{ height:6, borderRadius:3, background:"rgba(255,255,255,0.08)", overflow:"hidden" }}>
                    <div style={{
                      height:"100%", borderRadius:3,
                      width:`${confidence * 100}%`,
                      background: confidence > 0.7 ? "#10B981" : confidence > 0.4 ? "#F59E0B" : "#EF4444",
                      transition:"width .3s",
                    }} />
                  </div>
                </div>

                {/* Approve button */}
                <button
                  onClick={() => toggleApprove(idx)}
                  style={{
                    padding:"8px 16px", borderRadius:10,
                    fontSize:11, fontWeight:700, cursor:"pointer",
                    fontFamily:"'Public Sans',sans-serif",
                    border: isApproved ? "1px solid rgba(16,185,129,0.5)" : `1px solid ${T.cardBd}`,
                    background: isApproved ? "rgba(16,185,129,0.15)" : "transparent",
                    color: isApproved ? "#10B981" : T.muted,
                    transition:"all .2s",
                    display:"flex", alignItems:"center", gap:4,
                  }}
                >
                  <Icon n={isApproved ? "check_circle" : "radio_button_unchecked"} style={{ fontSize:16 }} />
                  {isApproved ? "Approved" : "Approve"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action buttons */}
      <div style={{ maxWidth:800, margin:"0 auto 48px", padding:"0 24px", display:"flex", gap:12, flexWrap:"wrap" }}>
        <button onClick={onBack} style={{
          padding:"14px 28px", borderRadius:12,
          fontSize:13, fontWeight:700, cursor:"pointer",
          background:"transparent", border:`1px solid ${T.cardBd}`,
          color:T.muted, fontFamily:"'Public Sans',sans-serif",
        }}>
          <Icon n="arrow_back" style={{ fontSize:16, verticalAlign:"middle", marginRight:6 }} />
          Back to Upload
        </button>

        <button onClick={approveAll} style={{
          padding:"14px 28px", borderRadius:12,
          fontSize:13, fontWeight:700, cursor:"pointer",
          background:"rgba(16,185,129,0.1)", border:"1px solid rgba(16,185,129,0.3)",
          color:"#10B981", fontFamily:"'Public Sans',sans-serif",
        }}>
          <Icon n="done_all" style={{ fontSize:16, verticalAlign:"middle", marginRight:6 }} />
          Approve All
        </button>

        <button
          onClick={handleConfirm}
          disabled={!allApproved}
          style={{
            flex:1, padding:"14px 28px", borderRadius:12,
            fontSize:14, fontWeight:800, cursor: allApproved ? "pointer" : "not-allowed",
            background: allApproved
              ? "linear-gradient(135deg, #ec5b13, #d4420a)"
              : (isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"),
            border:"none",
            color: allApproved ? "white" : T.muted,
            fontFamily:"'Public Sans',sans-serif",
            boxShadow: allApproved ? "0 4px 20px rgba(236,91,19,0.4)" : "none",
            transition:"all .2s",
          }}
        >
          <Icon n="rocket_launch" style={{ fontSize:18, verticalAlign:"middle", marginRight:8 }} />
          {allApproved ? "Start Full AI Analysis Pipeline" : "Approve all documents to continue"}
        </button>
      </div>
    </div>
  );
}
