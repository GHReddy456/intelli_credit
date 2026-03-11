import React, { useState } from "react";

/* ── Reusable styled sub-components ─────────────────── */
const FlagItem = ({ text, color = "#EF4444", icon = "●", isDark = true }) => (
  <div style={{
    display: "flex", alignItems: "flex-start", gap: 8,
    padding: "8px 12px", borderRadius: 10, marginBottom: 6,
    background: `${color}0A`, borderLeft: `3px solid ${color}50`,
  }}>
    <span style={{ color, fontSize:14, marginTop: 4, flexShrink: 0 }}>{icon}</span>
    <span style={{ fontSize:17, color: isDark ? "#cbd5e1" : "#334155", lineHeight: 1.5 }}>
      {typeof text === "string" ? text : (text?.message || text?.detail || JSON.stringify(text))}
    </span>
  </div>
);

const StatCard = ({ label, value, color = "#36cceb", isDark = true }) => (
  <div className="glass glass-hover" style={{
    padding: "14px 16px", borderRadius: 12, textAlign: "center", minWidth: 100,
  }}>
    <p style={{ fontSize:15, color: isDark ? "rgba(255,255,255,0.42)" : "#64748B", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 4, fontWeight: 600 }}>{label}</p>
    <p style={{ fontSize:21, fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
  </div>
);

const SectionCard = ({ title, children, color = "#36cceb", icon = "" }) => (
  <div className="glass" style={{ padding: "18px 20px", borderRadius: 16, marginBottom: 14 }}>
    <h3 style={{
      fontSize:17, fontWeight: 700, color, letterSpacing: "1px",
      textTransform: "uppercase", marginBottom: 14,
    }}>{icon} {title}</h3>
    {children}
  </div>
);

/* ── Formatting helpers ─────────────────────────── */
const fmtMoney = (n) => {
  if (typeof n !== "number" || isNaN(n)) return String(n);
  const abs = Math.abs(n);
  if (abs >= 1e7)  return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5)  return `₹${(n / 1e5).toFixed(2)} L`;
  return `₹${n.toLocaleString("en-IN")}`;
};
const fmtLabel = (s) =>
  String(s).replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

/* ── Structured flag card for audit flags ────────── */
const AuditFlagCard = ({ item, isDark = true }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#EF4444" isDark={isDark} />;
  const sev = item.severity || "MEDIUM";
  const col = sev === "HIGH" ? "#EF4444" : "#F59E0B";
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: `${col}08`, borderLeft: `3px solid ${col}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize:15, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
          background: col, color: "#fff", flexShrink: 0 }}>{sev}</span>
        <span style={{ fontSize:15, fontWeight: 700, color: isDark ? "#f1f5f9" : "#1E293B" }}>{fmtLabel(item.flag)}</span>
        {item.source && <span style={{ fontSize:16, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", marginLeft: "auto" }}>{item.source}</span>}
      </div>
      {item.section && (
        <p style={{ fontSize:16, color: isDark ? "rgba(255,255,255,0.42)" : "#64748B", marginBottom: 4 }}>
          Section: <strong>{fmtLabel(item.section)}</strong>
        </p>
      )}
      {item.context && (
        <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.5)" : "#475569", lineHeight: 1.65, fontStyle: "italic",
          borderTop: isDark ? "1px solid rgba(255,255,255,.06)" : "1px solid rgba(0,0,0,.06)", paddingTop: 6, marginTop: 4,
          wordBreak: "break-word" }}>
          &ldquo;{item.context.trim().replace(/\s+/g, " ").slice(0, 280)}{item.context.length > 280 ? "…" : ""}&rdquo;
        </p>
      )}
    </div>
  );
};

/* ── Structured flag card for governance flags ───── */
const GovernanceFlagCard = ({ item, isDark = true }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#F59E0B" isDark={isDark} />;
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: "rgba(245,158,11,.05)", borderLeft: "3px solid #F59E0B" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize:17, fontWeight: 700, color: "#f59e0b" }}>{fmtLabel(item.flag)}</span>
        {item.source && <span style={{ fontSize:16, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", marginLeft: "auto" }}>{item.source}</span>}
      </div>
      {item.section && (
        <p style={{ fontSize:16, color: isDark ? "rgba(255,255,255,0.42)" : "#64748B", marginBottom: 4 }}>
          Section: <strong>{fmtLabel(item.section)}</strong>
        </p>
      )}
      {item.context && (
        <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.5)" : "#475569", lineHeight: 1.65, fontStyle: "italic",
          borderTop: isDark ? "1px solid rgba(255,255,255,.06)" : "1px solid rgba(0,0,0,.06)", paddingTop: 6, marginTop: 4,
          wordBreak: "break-word" }}>
          &ldquo;{item.context.trim().replace(/\s+/g, " ").slice(0, 280)}{item.context.length > 280 ? "…" : ""}&rdquo;
        </p>
      )}
    </div>
  );
};

/* ── Key finding card for financial figures ──────── */
const FIG_LABELS = {
  revenue: "Revenue", ebitda: "EBITDA", pat: "PAT",
  total_debt: "Total Debt", net_profit: "Net Profit",
  turnover: "Turnover", itc: "ITC Claimed", tax_paid: "Tax Paid",
  gross_profit: "Gross Profit", current_ratio: "Current Ratio",
};
const KeyFindingCard = ({ item, isDark = true }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#0EA5E9" icon="→" isDark={isDark} />;
  const figures = item.figures || {};
  const hasFigures = Object.values(figures).some(v => v);
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: "rgba(14,165,233,.05)", borderLeft: "3px solid #0EA5E9" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: hasFigures ? 8 : 0 }}>
        <span style={{ fontSize:17, fontWeight: 700, color: "#36cceb" }}>
          {fmtLabel(item.doc_type || "Document")}
        </span>
        {item.source && <span style={{ fontSize:16, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8" }}>{item.source}</span>}
      </div>
      {hasFigures && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {Object.entries(figures).map(([k, v]) =>
            v ? (
              <span key={k} style={{ padding: "3px 10px", borderRadius: 6,
                background: "rgba(14,165,233,.15)", fontSize:16,
                color: "#36cceb", fontWeight: 600 }}>
                {FIG_LABELS[k] || fmtLabel(k)}: {fmtMoney(v)}
              </span>
            ) : null
          )}
        </div>
      )}
    </div>
  );
};

const AGENTS = [
  { id: "doc",    label: "Document Intelligence", icon: "📄", color: "#36cceb" },
  { id: "fraud",  label: "Fraud Detection",       icon: "🔒", color: "#EF4444" },
  { id: "promo",  label: "Promoter Intelligence", icon: "👥", color: "#8B5CF6" },
  { id: "sector", label: "Sector Intelligence",   icon: "🏭", color: "#0EA5E9" },
  { id: "res",    label: "Research",               icon: "🌐", color: "#059669" },
  { id: "verif",  label: "Verification",           icon: "✅", color: "#F59E0B" },
];

export default function AgentReports({ analysis, theme = "dark" }) {
  const isDark = theme !== "light";
  const [active, setActive] = useState("doc");
  const doc    = analysis?.document_agent || {};
  const fraud  = analysis?.fraud          || {};
  const promo  = analysis?.promoter       || {};
  const sector = analysis?.sector         || {};
  const res    = analysis?.research        || {};
  const tri    = analysis?.triangulation   || {};
  const pc     = analysis?.precognitive    || {};
  const sr     = analysis?.secondary_research || {};
  const verif  = analysis?.verification   || {};

  const activeAgent = AGENTS.find(a => a.id === active);

  return (
    <div>
      {/* Agent tab bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
        {AGENTS.map(a => (
          <button key={a.id} onClick={() => setActive(a.id)} style={{
            padding: "8px 16px", borderRadius: 10, fontSize:17, fontWeight: 600,
            cursor: "pointer", border: "none", whiteSpace: "nowrap",
            transition: "all .2s ease",
            background: active === a.id ? `${a.color}15` : isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
            color: active === a.id ? a.color : isDark ? "rgba(255,255,255,0.48)" : "#64748B",
            borderBottom: active === a.id ? `2px solid ${a.color}` : "2px solid transparent",
            boxShadow: active === a.id ? `0 0 12px ${a.color}20` : "0 1px 3px rgba(0,0,0,.06)",
          }}>
            {a.icon} {a.label}
          </button>
        ))}
      </div>

      {/* ── Document Intelligence ───────────────────────── */}
      {active === "doc" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Doc Risk" value={doc.overall_doc_risk || "LOW"} color={doc.overall_doc_risk === "HIGH" ? "#EF4444" : doc.overall_doc_risk === "MEDIUM" ? "#F59E0B" : "#10B981"} />
            <StatCard label="High Severity" value={doc.high_severity_count || 0} color={(doc.high_severity_count || 0) > 0 ? "#EF4444" : "#10B981"} />
            <StatCard label="Sections Found" value={Object.keys(doc.section_summaries || {}).length} />
          </div>

          <SectionCard title="Audit Flags" color="#EF4444" icon="🚩">
            {(doc.audit_flags || []).length > 0
              ? (doc.audit_flags || []).map((f, i) => <AuditFlagCard key={i} item={f} isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No audit flags detected.</p>}
          </SectionCard>

          <SectionCard title="Governance Flags" color="#F59E0B" icon="📋">
            {(doc.governance_flags || []).length > 0
              ? (doc.governance_flags || []).map((f, i) => <GovernanceFlagCard key={i} item={f} isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No governance flags.</p>}
          </SectionCard>

          {(doc.key_findings || []).length > 0 && (
            <SectionCard title="Key Findings" color="#0EA5E9" icon="🔍">
              {doc.key_findings.map((f, i) => <KeyFindingCard key={i} item={f} isDark={isDark} />)}
            </SectionCard>
          )}

          <SectionCard title="Summary" color="#36cceb" icon="📝">
            <p style={{ fontSize:15, color: isDark ? "#cbd5e1" : "#334155", lineHeight: 1.7 }}>
              {doc.llm_summary || `Overall document risk: ${doc.overall_doc_risk || "N/A"}. ${doc.high_severity_count || 0} high-severity issue(s) found.`}
            </p>
          </SectionCard>
        </div>
      )}

      {/* ── Fraud Detection ─────────────────────────────── */}
      {active === "fraud" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Fraud Score" value={`${(fraud.fraud_risk_score || 0).toFixed(1)}/100`}
              color={fraud.fraud_risk_score >= 70 ? "#991B1B" : fraud.fraud_risk_score >= 40 ? "#EF4444" : fraud.fraud_risk_score >= 20 ? "#F59E0B" : "#10B981"} isDark={isDark} />
            <StatCard label="Circular Trading" value={(fraud.circular_trading_score || 0).toFixed(3)} color="#EF4444" isDark={isDark} />
            <StatCard label="Benford Deviation" value={(fraud.benford_deviation_score || 0).toFixed(3)} color="#F59E0B" isDark={isDark} />
            <StatCard label="Bank Anomaly" value={(fraud.bank_anomaly_score || 0).toFixed(3)} color="#8B5CF6" isDark={isDark} />
          </div>

          <SectionCard title="Fraud Flags" color="#EF4444" icon="🚨">
            {(fraud.all_flags || []).length > 0
              ? (fraud.all_flags || []).map((f, i) => <FlagItem key={i} text={f} color="#EF4444" isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No fraud flags detected.</p>}
          </SectionCard>

          {fraud.is_hard_reject && (
            <div className="glass glow-red" style={{ padding: "14px 18px", borderRadius: 14, borderColor: "rgba(239,68,68,.3)" }}>
              <p style={{ fontSize:15, fontWeight: 700, color: "#EF4444" }}>⚠ FRAUD HARD REJECT — Critical anomalies detected</p>
            </div>
          )}
        </div>
      )}

      {/* ── Promoter Intelligence ───────────────────────── */}
      {active === "promo" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Network Risk" value={(promo.promoter_network_risk || 0).toFixed(3)} color="#8B5CF6" />
            <StatCard label="Promoters" value={promo.promoter_count || promo.graph_nodes || 0} color="#0891b2" />
            <StatCard label="Directors" value={promo.director_count || 0} color="#0ea5c9" />
            <StatCard label="Litigation Links" value={promo.litigation_links || analysis?.research?.litigation_count || 0} color="#EF4444" />
            <StatCard label="Graph Nodes" value={promo.graph_nodes || 0} color="#36cceb" />
          </div>

          {(promo.flags || []).length > 0 && (
            <SectionCard title="Promoter Flags" color="#EF4444" icon="🚩">
              {promo.flags.map((f, i) => <FlagItem key={i} text={f} color="#EF4444" isDark={isDark} />)}
            </SectionCard>
          )}

          <SectionCard title="Network Analysis" color="#8B5CF6" icon="🔗">
            <p style={{ fontSize:15, color: isDark ? "#cbd5e1" : "#334155", lineHeight: 1.7 }}>
              Promoter network consists of {promo.graph_nodes || 0} entities with {promo.graph_edges || 0} connections.
              {(promo.litigation_links || 0) > 0 && ` ${promo.litigation_links} litigation links detected.`}
              {(promo.promoter_network_risk || 0) > 0.5 ? " Elevated promoter risk — review recommended." : " Promoter risk within acceptable range."}
            </p>
          </SectionCard>
        </div>
      )}

      {/* ── Sector Intelligence ─────────────────────────── */}
      {active === "sector" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Sector" value={(sector.sector || "Unknown").replace(/_/g, " ")} color="#0EA5E9" />
            <StatCard label="Risk Score" value={(sector.sector_risk_score || 0).toFixed(2)} color={sector.sector_risk_score > 0.6 ? "#EF4444" : "#10B981"} />
            <StatCard label="Outlook" value={sector.sector_outlook || "N/A"} color="#36cceb" />
            <StatCard label="Regulatory Issues" value={sector.regulatory_violation_count || 0} color="#F59E0B" />
          </div>

          <SectionCard title="Sector Conditions" color="#0EA5E9" icon="📊">
            <p style={{ fontSize:15, color: isDark ? "#cbd5e1" : "#334155", lineHeight: 1.7 }}>
              {sector.conditions_summary || "No sector conditions summary available."}
            </p>
          </SectionCard>

          {(sector.headwinds || []).length > 0 && (
            <SectionCard title="Headwinds" color="#EF4444" icon="⬇">
              {sector.headwinds.map((h, i) => <FlagItem key={i} text={h} color="#EF4444" icon="↓" isDark={isDark} />)}
            </SectionCard>
          )}

          {(sector.tailwinds || []).length > 0 && (
            <SectionCard title="Tailwinds" color="#10B981" icon="⬆">
              {sector.tailwinds.map((t, i) => <FlagItem key={i} text={t} color="#10B981" icon="↑" isDark={isDark} />)}
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Research ────────────────────────────────────── */}
      {active === "res" && (
        <div className="fade-in-up">
          {/* Top-line stats */}
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="News Sentiment" value={(res.news_sentiment_score || 0).toFixed(3)} color={res.news_sentiment_score > 0.6 ? "#EF4444" : "#10B981"} />
            <StatCard label="Macro Risk Score" value={(sr.macro_risk_score || 0).toFixed(2)} color={(sr.macro_risk_score || 0) > 0.5 ? "#EF4444" : "#10B981"} />
            <StatCard label="Pre-Cognitive Risk" value={(pc.precognitive_risk_score || 0).toFixed(2)} color={(pc.precognitive_risk_score || 0) > 0.5 ? "#EF4444" : "#F59E0B"} />
            <StatCard label="Triangulation Risk" value={(tri.triangulation_risk || 0).toFixed(2)} color={(tri.triangulation_risk || 0) > 0.4 ? "#EF4444" : "#10B981"} />
            <StatCard label="Critical Warnings" value={pc.critical_count || 0} color="#EF4444" />
          </div>

          {/* Macro environment */}
          <SectionCard title="Macro Environment (Alpha Vantage)" color="#0EA5E9" icon="🌍">
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10 }}>
              {[
                { label: "Rate Environment", val: sr.rate_environment },
                { label: "GDP Signal",        val: sr.gdp_signal },
                { label: "Banking Health",    val: sr.banking_health },
                { label: "Company Trend",     val: sr.company_rating_trend },
                { label: "Sector CR Quality", val: sr.sector_credit_quality },
              ].map((item, i) => (
                <div key={i} style={{
                  padding: "8px 14px", borderRadius: 8, fontSize: 15, fontWeight: 600,
                  background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.04)",
                  color: item.val === "DETERIORATING" || item.val === "HAWKISH" || item.val === "STRESS" ? "#EF4444"
                       : item.val === "IMPROVING"    || item.val === "DOVISH"  || item.val === "STABLE"  ? "#10B981"
                       : isDark ? "#f1f5f9" : "#1e293b",
                }}>
                  <span style={{ fontWeight: 400, fontSize: 13, display: "block", color: isDark ? "rgba(255,255,255,0.5)" : "#64748b" }}>{item.label}</span>
                  {item.val || "—"}
                </div>
              ))}
            </div>
            {(sr.macro_signals || []).map((sig, i) => (
              <div key={i} style={{ padding: "5px 10px", borderLeft: "3px solid #0EA5E9", marginBottom: 4, fontSize: 15 }}>
                <b style={{ color: isDark ? "#e2e8f0" : "#1e293b" }}>{sig.category}:</b>{" "}
                <span style={{ color: isDark ? "rgba(255,255,255,0.7)" : "#475569" }}>{sig.headline}</span>
              </div>
            ))}
          </SectionCard>

          {/* Credit Rating Intelligence */}
          {(sr.rating_signals || []).length > 0 && (
            <SectionCard title="Credit Rating Intelligence (Finnhub + NewsAPI)" color="#8B5CF6" icon="📊">
              {(sr.rating_mentions || []).length > 0 && (
                <p style={{ fontSize: 15, marginBottom: 8, color: isDark ? "#e2e8f0" : "#1e293b" }}>
                  Rating mentions: <b>{sr.rating_mentions.join(", ")}</b>
                </p>
              )}
              {sr.rating_signals.map((sig, i) => (
                <div key={i} style={{
                  padding: "8px 12px", borderRadius: 8, marginBottom: 5,
                  background: sig.trend === "DETERIORATING" ? "rgba(239,68,68,0.07)" : sig.trend === "IMPROVING" ? "rgba(16,185,129,0.07)" : (isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"),
                  borderLeft: `3px solid ${sig.trend === "DETERIORATING" ? "#EF4444" : sig.trend === "IMPROVING" ? "#10B981" : "#8B5CF6"}`,
                }}>
                  <span style={{ fontSize: 15, fontWeight: 600, color: isDark ? "#f1f5f9" : "#1e293b" }}>{sig.title}</span>
                  <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 700,
                    color: sig.trend === "DETERIORATING" ? "#EF4444" : sig.trend === "IMPROVING" ? "#10B981" : "#94A3B8" }}>{sig.trend}</span>
                  {sig.source && <span style={{ marginLeft: 8, fontSize: 12, color: "#94A3B8" }}>{sig.source}</span>}
                </div>
              ))}
            </SectionCard>
          )}

          {/* News Articles */}
          {(sr.top_news || res.articles || []).length > 0 && (
            <SectionCard title="News Sentiment (NewsAPI + Finnhub + DDGS)" color="#0EA5E9" icon="📰">
              {(sr.top_news || res.articles || []).map((a, i) => (
                <div key={i} style={{
                  padding: "8px 12px", borderRadius: 10, marginBottom: 6,
                  background: a.sentiment === "NEGATIVE" ? "rgba(239,68,68,.06)" : a.sentiment === "POSITIVE" ? "rgba(16,185,129,.06)" : "rgba(0,0,0,.02)",
                  borderLeft: `3px solid ${a.sentiment === "NEGATIVE" ? "#EF4444" : a.sentiment === "POSITIVE" ? "#10B981" : "#94A3B8"}`,
                }}>
                  <p style={{ fontSize: 15, color: isDark ? "#f1f5f9" : "#1E293B", fontWeight: 600, marginBottom: 2 }}>{a.title || a.url}</p>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={{
                      fontSize: 13, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                      background: a.sentiment === "NEGATIVE" ? "rgba(239,68,68,0.15)" : a.sentiment === "POSITIVE" ? "rgba(16,185,129,0.15)" : isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.06)",
                      color: a.sentiment === "NEGATIVE" ? "#ef4444" : a.sentiment === "POSITIVE" ? "#10b981" : isDark ? "rgba(255,255,255,0.5)" : "#64748B",
                    }}>{a.sentiment || "NEUTRAL"}</span>
                    {a.source && <span style={{ fontSize: 12, color: "#94A3B8" }}>{a.source}</span>}
                  </div>
                </div>
              ))}
            </SectionCard>
          )}

          {/* Triangulation */}
          {(tri.signals || []).length > 0 && (
            <SectionCard title="Data Triangulation (Document ↔ External Sources)" color="#F59E0B" icon="🔺">
              <div style={{ display: "flex", gap: 12, marginBottom: 10, flexWrap: "wrap" }}>
                {[
                  { label: "Corroborated", val: tri.corroborated_count, color: "#10B981" },
                  { label: "Discrepancies", val: tri.discrepancy_count, color: "#EF4444" },
                  { label: "Unverified", val: tri.unverified_count, color: "#F59E0B" },
                ].map((x, i) => (
                  <div key={i} style={{ padding: "6px 14px", borderRadius: 8, background: `${x.color}15`, color: x.color, fontWeight: 700, fontSize: 15 }}>
                    {x.label}: {x.val || 0}
                  </div>
                ))}
              </div>
              {tri.signals.slice(0, 6).map((sig, i) => (
                <div key={i} style={{
                  padding: "8px 12px", borderRadius: 8, marginBottom: 5,
                  background: sig.status === "DISCREPANCY" ? "rgba(239,68,68,0.07)" : sig.status === "CORROBORATED" ? "rgba(16,185,129,0.07)" : (isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"),
                  borderLeft: `3px solid ${sig.status === "DISCREPANCY" ? "#EF4444" : sig.status === "CORROBORATED" ? "#10B981" : "#F59E0B"}`,
                }}>
                  <span style={{ fontWeight: 700, fontSize: 13,
                    color: sig.status === "DISCREPANCY" ? "#EF4444" : sig.status === "CORROBORATED" ? "#10B981" : "#F59E0B" }}>
                    {sig.status}
                  </span>
                  <span style={{ marginLeft: 8, fontWeight: 600, color: isDark ? "#e2e8f0" : "#1e293b", fontSize: 14 }}>{sig.signal_type}</span>
                  {sig.detail && <p style={{ margin: "2px 0 0", fontSize: 13, color: isDark ? "rgba(255,255,255,0.6)" : "#64748B" }}>{sig.detail}</p>}
                </div>
              ))}
            </SectionCard>
          )}

          {/* Pre-Cognitive Early Warnings */}
          {(pc.signals || []).length > 0 && (
            <SectionCard title="Pre-Cognitive Early Warning Signals" color="#EF4444" icon="⚡">
              <p style={{ fontSize: 13, color: isDark ? "rgba(255,255,255,0.5)" : "#64748b", marginBottom: 10 }}>
                Risk score: <b style={{ color: isDark ? "#f1f5f9" : "#1e293b" }}>{(pc.precognitive_risk_score || 0).toFixed(2)}</b>
                {" · "}CRITICAL: <b style={{ color: "#EF4444" }}>{pc.critical_count || 0}</b>
                {" · "}HIGH: <b style={{ color: "#F59E0B" }}>{pc.high_count || 0}</b>
              </p>
              {pc.signals.map((sig, i) => (
                <div key={i} style={{
                  padding: "10px 14px", borderRadius: 10, marginBottom: 8,
                  background: sig.severity === "CRITICAL" ? "rgba(239,68,68,0.08)" : sig.severity === "HIGH" ? "rgba(245,158,11,0.08)" : (isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"),
                  borderLeft: `4px solid ${sig.severity === "CRITICAL" ? "#EF4444" : sig.severity === "HIGH" ? "#F59E0B" : "#3B82F6"}`,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
                      background: sig.severity === "CRITICAL" ? "rgba(239,68,68,0.18)" : sig.severity === "HIGH" ? "rgba(245,158,11,0.18)" : "rgba(59,130,246,0.18)",
                      color: sig.severity === "CRITICAL" ? "#EF4444" : sig.severity === "HIGH" ? "#F59E0B" : "#3B82F6",
                    }}>{sig.severity}</span>
                    <span style={{ fontWeight: 700, fontSize: 15, color: isDark ? "#f1f5f9" : "#1e293b" }}>{sig.title}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: 13, color: isDark ? "rgba(255,255,255,0.65)" : "#475569" }}>{sig.description}</p>
                  {sig.action && (
                    <p style={{ margin: "4px 0 0", fontSize: 12, color: isDark ? "rgba(255,255,255,0.45)" : "#64748b", fontStyle: "italic" }}>
                      → {sig.action}
                    </p>
                  )}
                </div>
              ))}
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Verification ────────────────────────────────── */}
      {active === "verif" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Overall Severity" value={verif.overall_severity || "LOW"}
              color={verif.overall_severity === "HIGH" ? "#EF4444" : verif.overall_severity === "MEDIUM" ? "#F59E0B" : "#10B981"} />
            <StatCard label="Total Flags" value={verif.total_flags || 0} color="#F59E0B" />
          </div>

          <SectionCard title="GST–Bank Cross-check" color="#F59E0B" icon="🧾">
            {(verif.gst_bank?.flags || []).length > 0
              ? verif.gst_bank.flags.map((f, i) => <FlagItem key={i} text={f} color="#F59E0B" isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No GST-bank mismatches.</p>}
          </SectionCard>

          <SectionCard title="ITR Cross-check" color="#F59E0B" icon="📋">
            {(verif.itr?.flags || []).length > 0
              ? verif.itr.flags.map((f, i) => <FlagItem key={i} text={f} color="#F59E0B" isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No ITR mismatches.</p>}
          </SectionCard>

          <SectionCard title="GSTR-2A vs 3B" color="#EF4444" icon="⚠">
            {(verif.gstr2a_3b?.flags || []).length > 0
              ? verif.gstr2a_3b.flags.map((f, i) => <FlagItem key={i} text={f} color="#EF4444" isDark={isDark} />)
              : <p style={{ fontSize:17, color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8", fontStyle: "italic" }}>No GSTR-2A/3B mismatches.</p>}
          </SectionCard>
        </div>
      )}
    </div>
  );
}
