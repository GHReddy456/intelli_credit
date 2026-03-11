import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API = axios.create({ baseURL: "/api" });

function Icon({ n, style = {} }) {
  return <span className="material-symbols-outlined" style={{ userSelect:"none", ...style }}>{n}</span>;
}

const DEFAULT_SCHEMAS = {
  annual_report: [
    { label: "corporate_overview",     keywords: ["corporate overview", "company overview", "about us"] },
    { label: "directors_report",       keywords: ["directors' report", "board's report"] },
    { label: "auditors_report",        keywords: ["independent auditor", "audit report"] },
    { label: "balance_sheet",          keywords: ["balance sheet", "assets and liabilities"] },
    { label: "profit_loss",            keywords: ["profit and loss", "income statement"] },
    { label: "cash_flow",              keywords: ["cash flow statement", "cash flows from"] },
    { label: "notes_to_accounts",      keywords: ["notes to accounts", "accounting policies"] },
    { label: "shareholding_pattern",   keywords: ["shareholding pattern", "promoter holding"] },
  ],
  alm: [
    { label: "maturity_profile",       keywords: ["maturity profile", "maturity bucket", "time bucket"] },
    { label: "asset_classification",   keywords: ["asset classification", "performing assets", "npa"] },
    { label: "liability_structure",    keywords: ["liability structure", "deposit profile"] },
    { label: "gap_analysis",           keywords: ["cumulative gap", "gap analysis", "mismatch"] },
  ],
  shareholding_pattern: [
    { label: "promoter_holding",       keywords: ["promoter", "promoter group", "promoter holding"] },
    { label: "institutional_holding",  keywords: ["institutional", "fii", "dii", "mutual fund"] },
    { label: "public_holding",         keywords: ["public", "non-promoter", "retail"] },
    { label: "pledge_details",         keywords: ["pledge", "encumbered", "pledged shares"] },
  ],
  borrowing_profile: [
    { label: "fund_based",             keywords: ["fund based", "term loan", "working capital", "cash credit"] },
    { label: "non_fund_based",         keywords: ["non fund", "letter of credit", "bank guarantee", "lc", "bg"] },
    { label: "repayment_schedule",     keywords: ["repayment", "emi", "installment", "maturity"] },
    { label: "covenant_compliance",    keywords: ["covenant", "compliance", "dscr", "debt equity"] },
  ],
  portfolio_performance: [
    { label: "portfolio_summary",      keywords: ["portfolio summary", "aum", "assets under management"] },
    { label: "performance_metrics",    keywords: ["return", "yield", "irr", "performance", "benchmark"] },
    { label: "sector_allocation",      keywords: ["sector allocation", "industry exposure", "concentration"] },
    { label: "risk_metrics",           keywords: ["risk", "var", "volatility", "sharpe", "drawdown"] },
  ],
  gst: [
    { label: "gstr3b_summary",         keywords: ["gstr-3b", "tax payable", "tax paid"] },
    { label: "itc_details",            keywords: ["input tax credit", "itc claimed"] },
    { label: "annual_return",          keywords: ["gstr-9", "annual return", "aggregate turnover"] },
  ],
  bank_statement: [
    { label: "account_summary",        keywords: ["account summary", "opening balance"] },
    { label: "transaction_history",    keywords: ["transaction", "debit", "credit"] },
    { label: "cheque_returns",         keywords: ["cheque return", "dishonor"] },
  ],
  itr: [
    { label: "income_from_business",   keywords: ["income from business", "net profit"] },
    { label: "tax_computation",        keywords: ["tax computation", "total tax", "tds"] },
    { label: "depreciation",           keywords: ["depreciation", "block of assets"] },
  ],
  legal: [
    { label: "case_header",            keywords: ["court", "tribunal", "nclt"] },
    { label: "relief_claimed",         keywords: ["relief", "prayer", "recovery"] },
    { label: "court_order",            keywords: ["ordered", "directed", "judgment"] },
  ],
};

export default function SchemaEditor({ theme = "dark" }) {
  const isDark = theme === "dark";
  const [schemas, setSchemas] = useState(DEFAULT_SCHEMAS);
  const [expandedType, setExpandedType] = useState(null);
  const [editingSection, setEditingSection] = useState(null); // { type, idx }
  const [newKeyword, setNewKeyword] = useState("");
  const [saveStatus, setSaveStatus] = useState(null); // "saving" | "saved" | "error"

  const T = {
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

  // Load schemas from backend on mount
  useEffect(() => {
    API.get("/schema").then(r => {
      if (r.data && r.data.schemas) setSchemas(r.data.schemas);
    }).catch(() => {});
  }, []);

  const handleSave = useCallback(async () => {
    setSaveStatus("saving");
    try {
      await API.put("/schema", { schemas });
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus(null), 2000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus(null), 3000);
    }
  }, [schemas]);

  const handleReset = () => {
    setSchemas(DEFAULT_SCHEMAS);
    setSaveStatus(null);
  };

  const addKeyword = (docType, sectionIdx) => {
    if (!newKeyword.trim()) return;
    setSchemas(prev => {
      const updated = { ...prev };
      const sections = [...updated[docType]];
      sections[sectionIdx] = {
        ...sections[sectionIdx],
        keywords: [...sections[sectionIdx].keywords, newKeyword.trim().toLowerCase()],
      };
      updated[docType] = sections;
      return updated;
    });
    setNewKeyword("");
  };

  const removeKeyword = (docType, sectionIdx, kwIdx) => {
    setSchemas(prev => {
      const updated = { ...prev };
      const sections = [...updated[docType]];
      sections[sectionIdx] = {
        ...sections[sectionIdx],
        keywords: sections[sectionIdx].keywords.filter((_, i) => i !== kwIdx),
      };
      updated[docType] = sections;
      return updated;
    });
  };

  const addSection = (docType) => {
    const label = prompt("Enter section label (e.g. risk_metrics):");
    if (!label) return;
    setSchemas(prev => ({
      ...prev,
      [docType]: [...(prev[docType] || []), { label: label.trim().toLowerCase().replace(/\s+/g, "_"), keywords: [] }],
    }));
  };

  const removeSection = (docType, idx) => {
    setSchemas(prev => ({
      ...prev,
      [docType]: prev[docType].filter((_, i) => i !== idx),
    }));
  };

  const fmtLabel = s => String(s).replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  const TYPE_ICONS = {
    annual_report: "analytics", alm: "account_balance", shareholding_pattern: "pie_chart",
    borrowing_profile: "request_quote", portfolio_performance: "trending_up",
    gst: "receipt_long", bank_statement: "account_balance", itr: "description",
    legal: "gavel", sanction_letter: "verified",
  };
  const TYPE_COLORS = {
    annual_report: "#a855f7", alm: "#0891b2", shareholding_pattern: "#059669",
    borrowing_profile: "#D97706", portfolio_performance: "#7C3AED",
    gst: "#60a5fa", bank_statement: "#4ade80", itr: "#fb923c",
    legal: "#f87171", sanction_letter: "#ec5b13",
  };

  return (
    <div style={{ maxWidth:900, margin:"0 auto" }}>
      {/* Header */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20, flexWrap:"wrap", gap:12 }}>
        <div>
          <h2 style={{ margin:0, fontSize:22, fontWeight:800, color:T.color }}>
            <Icon n="schema" style={{ fontSize:24, verticalAlign:"middle", marginRight:8, color:"#ec5b13" }} />
            Dynamic Schema Editor
          </h2>
          <p style={{ margin:"4px 0 0", fontSize:13, color:T.muted }}>
            Configure extraction schemas for each document type. Changes affect how documents are parsed and structured.
          </p>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <button onClick={handleReset} style={{
            padding:"8px 16px", borderRadius:8, fontSize:12, fontWeight:700, cursor:"pointer",
            background:"transparent", border:`1px solid ${T.cardBd}`, color:T.muted,
            fontFamily:"'Public Sans',sans-serif",
          }}>Reset Defaults</button>
          <button onClick={handleSave} style={{
            padding:"8px 20px", borderRadius:8, fontSize:12, fontWeight:700, cursor:"pointer",
            background: saveStatus === "saved" ? "rgba(16,185,129,0.15)" : "rgba(236,91,19,0.15)",
            border: `1px solid ${saveStatus === "saved" ? "rgba(16,185,129,0.4)" : "rgba(236,91,19,0.4)"}`,
            color: saveStatus === "saved" ? "#10B981" : "#ec5b13",
            fontFamily:"'Public Sans',sans-serif",
          }}>
            {saveStatus === "saving" ? "Saving…" : saveStatus === "saved" ? "✓ Saved" : saveStatus === "error" ? "✗ Error" : "Save Schema"}
          </button>
        </div>
      </div>

      {/* Schema types accordion */}
      {Object.entries(schemas).map(([docType, sections]) => {
        const isExpanded = expandedType === docType;
        const color = TYPE_COLORS[docType] || "#94a3b8";
        const icon = TYPE_ICONS[docType] || "description";

        return (
          <div key={docType} style={{ ...glass, borderRadius:14, marginBottom:10, overflow:"hidden" }}>
            {/* Type header */}
            <div
              onClick={() => setExpandedType(isExpanded ? null : docType)}
              style={{
                padding:"16px 20px", cursor:"pointer",
                display:"flex", alignItems:"center", justifyContent:"space-between",
                background: isExpanded ? `${color}10` : "transparent",
                transition:"background .2s",
              }}
            >
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{
                  width:36, height:36, borderRadius:10, background:`${color}20`,
                  display:"flex", alignItems:"center", justifyContent:"center",
                }}>
                  <Icon n={icon} style={{ color, fontSize:20 }} />
                </div>
                <div>
                  <div style={{ fontSize:14, fontWeight:700, color:T.color }}>{fmtLabel(docType)}</div>
                  <div style={{ fontSize:11, color:T.muted }}>{sections.length} sections configured</div>
                </div>
              </div>
              <Icon n={isExpanded ? "expand_less" : "expand_more"} style={{ color:T.muted, fontSize:24 }} />
            </div>

            {/* Sections */}
            {isExpanded && (
              <div style={{ padding:"0 20px 16px" }}>
                {sections.map((section, sIdx) => {
                  const isEditing = editingSection?.type === docType && editingSection?.idx === sIdx;
                  return (
                    <div key={sIdx} style={{
                      padding:"12px 16px", borderRadius:10, marginBottom:8,
                      background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)",
                      border: `1px solid ${isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"}`,
                    }}>
                      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:8 }}>
                        <span style={{ fontSize:13, fontWeight:700, color }}>{fmtLabel(section.label)}</span>
                        <div style={{ display:"flex", gap:4 }}>
                          <button
                            onClick={() => setEditingSection(isEditing ? null : { type: docType, idx: sIdx })}
                            style={{
                              background:"none", border:"none", cursor:"pointer", padding:2,
                              color: isEditing ? "#ec5b13" : T.muted,
                            }}
                          >
                            <Icon n={isEditing ? "close" : "edit"} style={{ fontSize:16 }} />
                          </button>
                          <button
                            onClick={() => removeSection(docType, sIdx)}
                            style={{ background:"none", border:"none", cursor:"pointer", padding:2, color:"#EF4444" }}
                          >
                            <Icon n="delete_outline" style={{ fontSize:16 }} />
                          </button>
                        </div>
                      </div>
                      {/* Keywords */}
                      <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                        {section.keywords.map((kw, kwIdx) => (
                          <span key={kwIdx} style={{
                            display:"inline-flex", alignItems:"center", gap:4,
                            padding:"3px 10px", borderRadius:12,
                            background:`${color}15`, color,
                            fontSize:11, fontWeight:600,
                          }}>
                            {kw}
                            {isEditing && (
                              <button onClick={() => removeKeyword(docType, sIdx, kwIdx)} style={{
                                background:"none", border:"none", cursor:"pointer", padding:0,
                                color:"#EF4444", fontSize:12, lineHeight:1,
                              }}>×</button>
                            )}
                          </span>
                        ))}
                      </div>
                      {/* Add keyword input */}
                      {isEditing && (
                        <div style={{ display:"flex", gap:6, marginTop:8 }}>
                          <input
                            value={newKeyword}
                            onChange={e => setNewKeyword(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && addKeyword(docType, sIdx)}
                            placeholder="Add keyword…"
                            style={{
                              flex:1, padding:"6px 10px", borderRadius:6,
                              background:T.inputBg, color:T.color,
                              border:`1px solid ${T.inputBd}`,
                              fontSize:12, fontFamily:"'Public Sans',sans-serif", outline:"none",
                            }}
                          />
                          <button onClick={() => addKeyword(docType, sIdx)} style={{
                            padding:"6px 12px", borderRadius:6,
                            background:"rgba(236,91,19,0.15)", border:"1px solid rgba(236,91,19,0.3)",
                            color:"#ec5b13", fontSize:11, fontWeight:700, cursor:"pointer",
                            fontFamily:"'Public Sans',sans-serif",
                          }}>Add</button>
                        </div>
                      )}
                    </div>
                  );
                })}
                {/* Add section button */}
                <button onClick={() => addSection(docType)} style={{
                  width:"100%", padding:"10px", borderRadius:10,
                  border:`1px dashed ${color}40`, background:"transparent",
                  color, fontSize:12, fontWeight:700, cursor:"pointer",
                  fontFamily:"'Public Sans',sans-serif",
                }}>
                  <Icon n="add" style={{ fontSize:16, verticalAlign:"middle", marginRight:4 }} />
                  Add Section
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
