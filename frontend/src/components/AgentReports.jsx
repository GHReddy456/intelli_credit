import React, { useState } from "react";

/* ── Reusable styled sub-components ─────────────────── */
const FlagItem = ({ text, color = "#EF4444", icon = "●" }) => (
  <div style={{
    display: "flex", alignItems: "flex-start", gap: 8,
    padding: "8px 12px", borderRadius: 10, marginBottom: 6,
    background: `${color}0A`, borderLeft: `3px solid ${color}50`,
  }}>
    <span style={{ color, fontSize: 8, marginTop: 4, flexShrink: 0 }}>{icon}</span>
    <span style={{ fontSize: 11, color: "#334155", lineHeight: 1.5 }}>
      {typeof text === "string" ? text : (text?.message || text?.detail || JSON.stringify(text))}
    </span>
  </div>
);

const StatCard = ({ label, value, color = "#36cceb" }) => (
  <div className="glass glass-hover" style={{
    padding: "14px 16px", borderRadius: 12, textAlign: "center", minWidth: 100,
  }}>
    <p style={{ fontSize: 9, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 4, fontWeight: 600 }}>{label}</p>
    <p style={{ fontSize: 18, fontWeight: 800, color, lineHeight: 1 }}>{value}</p>
  </div>
);

const SectionCard = ({ title, children, color = "#36cceb", icon = "" }) => (
  <div className="glass" style={{ padding: "18px 20px", borderRadius: 16, marginBottom: 14 }}>
    <h3 style={{
      fontSize: 11, fontWeight: 700, color, letterSpacing: "1px",
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
const AuditFlagCard = ({ item }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#EF4444" />;
  const sev = item.severity || "MEDIUM";
  const col = sev === "HIGH" ? "#EF4444" : "#F59E0B";
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: `${col}08`, borderLeft: `3px solid ${col}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
          background: col, color: "#fff", flexShrink: 0 }}>{sev}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: "#0F172A" }}>{fmtLabel(item.flag)}</span>
        {item.source && <span style={{ fontSize: 10, color: "#94A3B8", marginLeft: "auto" }}>{item.source}</span>}
      </div>
      {item.section && (
        <p style={{ fontSize: 10, color: "#64748B", marginBottom: 4 }}>
          Section: <strong>{fmtLabel(item.section)}</strong>
        </p>
      )}
      {item.context && (
        <p style={{ fontSize: 11, color: "#475569", lineHeight: 1.65, fontStyle: "italic",
          borderTop: "1px solid rgba(0,0,0,.05)", paddingTop: 6, marginTop: 4,
          wordBreak: "break-word" }}>
          &ldquo;{item.context.trim().replace(/\s+/g, " ").slice(0, 280)}{item.context.length > 280 ? "…" : ""}&rdquo;
        </p>
      )}
    </div>
  );
};

/* ── Structured flag card for governance flags ───── */
const GovernanceFlagCard = ({ item }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#F59E0B" />;
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: "rgba(245,158,11,.05)", borderLeft: "3px solid #F59E0B" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "#B45309" }}>{fmtLabel(item.flag)}</span>
        {item.source && <span style={{ fontSize: 10, color: "#94A3B8", marginLeft: "auto" }}>{item.source}</span>}
      </div>
      {item.section && (
        <p style={{ fontSize: 10, color: "#64748B", marginBottom: 4 }}>
          Section: <strong>{fmtLabel(item.section)}</strong>
        </p>
      )}
      {item.context && (
        <p style={{ fontSize: 11, color: "#475569", lineHeight: 1.65, fontStyle: "italic",
          borderTop: "1px solid rgba(0,0,0,.05)", paddingTop: 6, marginTop: 4,
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
const KeyFindingCard = ({ item }) => {
  if (typeof item === "string") return <FlagItem text={item} color="#0EA5E9" icon="→" />;
  const figures = item.figures || {};
  const hasFigures = Object.values(figures).some(v => v);
  return (
    <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8,
      background: "rgba(14,165,233,.05)", borderLeft: "3px solid #0EA5E9" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: hasFigures ? 8 : 0 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "#0369A1" }}>
          {fmtLabel(item.doc_type || "Document")}
        </span>
        {item.source && <span style={{ fontSize: 10, color: "#94A3B8" }}>{item.source}</span>}
      </div>
      {hasFigures && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {Object.entries(figures).map(([k, v]) =>
            v ? (
              <span key={k} style={{ padding: "3px 10px", borderRadius: 6,
                background: "rgba(14,165,233,.12)", fontSize: 10,
                color: "#0369A1", fontWeight: 600 }}>
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

export default function AgentReports({ analysis }) {
  const [active, setActive] = useState("doc");
  const doc    = analysis?.document_agent || {};
  const fraud  = analysis?.fraud          || {};
  const promo  = analysis?.promoter       || {};
  const sector = analysis?.sector         || {};
  const res    = analysis?.research       || {};
  const verif  = analysis?.verification   || {};

  const activeAgent = AGENTS.find(a => a.id === active);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      {/* Agent tab bar */}
      <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
        {AGENTS.map(a => (
          <button key={a.id} onClick={() => setActive(a.id)} style={{
            padding: "8px 16px", borderRadius: 10, fontSize: 11, fontWeight: 600,
            cursor: "pointer", border: "none", whiteSpace: "nowrap",
            transition: "all .2s ease",
            background: active === a.id ? `${a.color}15` : "#FFFFFF",
            color: active === a.id ? a.color : "#64748B",
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
              ? (doc.audit_flags || []).map((f, i) => <AuditFlagCard key={i} item={f} />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No audit flags detected.</p>}
          </SectionCard>

          <SectionCard title="Governance Flags" color="#F59E0B" icon="📋">
            {(doc.governance_flags || []).length > 0
              ? (doc.governance_flags || []).map((f, i) => <GovernanceFlagCard key={i} item={f} />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No governance flags.</p>}
          </SectionCard>

          {(doc.key_findings || []).length > 0 && (
            <SectionCard title="Key Findings" color="#0EA5E9" icon="🔍">
              {doc.key_findings.map((f, i) => <KeyFindingCard key={i} item={f} />)}
            </SectionCard>
          )}

          <SectionCard title="Summary" color="#36cceb" icon="📝">
            <p style={{ fontSize: 12, color: "#334155", lineHeight: 1.7 }}>
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
              color={fraud.fraud_risk_score > 50 ? "#EF4444" : fraud.fraud_risk_score > 25 ? "#F59E0B" : "#10B981"} />
            <StatCard label="Circular Trading" value={(fraud.circular_trading_score || 0).toFixed(3)} color="#EF4444" />
            <StatCard label="Benford Deviation" value={(fraud.benford_deviation_score || 0).toFixed(3)} color="#F59E0B" />
            <StatCard label="Bank Anomaly" value={(fraud.bank_anomaly_score || 0).toFixed(3)} color="#8B5CF6" />
          </div>

          <SectionCard title="Fraud Flags" color="#EF4444" icon="🚨">
            {(fraud.all_flags || []).length > 0
              ? (fraud.all_flags || []).map((f, i) => <FlagItem key={i} text={f} color="#EF4444" />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No fraud flags detected.</p>}
          </SectionCard>

          {fraud.is_hard_reject && (
            <div className="glass glow-red" style={{ padding: "14px 18px", borderRadius: 14, borderColor: "rgba(239,68,68,.3)" }}>
              <p style={{ fontSize: 12, fontWeight: 700, color: "#EF4444" }}>⚠ FRAUD HARD REJECT — Critical anomalies detected</p>
            </div>
          )}
        </div>
      )}

      {/* ── Promoter Intelligence ───────────────────────── */}
      {active === "promo" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="Network Risk" value={(promo.promoter_network_risk || 0).toFixed(3)} color="#8B5CF6" />
            <StatCard label="Promoters" value={promo.promoter_count || 0} color="#0891b2" />
            <StatCard label="Directors" value={promo.director_count || 0} color="#0ea5c9" />
            <StatCard label="Litigation Links" value={promo.litigation_links || 0} color="#EF4444" />
            <StatCard label="Graph Nodes" value={promo.graph_nodes || 0} color="#36cceb" />
          </div>

          {(promo.flags || []).length > 0 && (
            <SectionCard title="Promoter Flags" color="#EF4444" icon="🚩">
              {promo.flags.map((f, i) => <FlagItem key={i} text={f} color="#EF4444" />)}
            </SectionCard>
          )}

          <SectionCard title="Network Analysis" color="#8B5CF6" icon="🔗">
            <p style={{ fontSize: 12, color: "#334155", lineHeight: 1.7 }}>
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
            <p style={{ fontSize: 12, color: "#334155", lineHeight: 1.7 }}>
              {sector.conditions_summary || "No sector conditions summary available."}
            </p>
          </SectionCard>

          {(sector.headwinds || []).length > 0 && (
            <SectionCard title="Headwinds" color="#EF4444" icon="⬇">
              {sector.headwinds.map((h, i) => <FlagItem key={i} text={h} color="#EF4444" icon="↓" />)}
            </SectionCard>
          )}

          {(sector.tailwinds || []).length > 0 && (
            <SectionCard title="Tailwinds" color="#10B981" icon="⬆">
              {sector.tailwinds.map((t, i) => <FlagItem key={i} text={t} color="#10B981" icon="↑" />)}
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Research ────────────────────────────────────── */}
      {active === "res" && (
        <div className="fade-in-up">
          <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <StatCard label="News Sentiment" value={(res.news_sentiment_score || 0).toFixed(3)} color={res.news_sentiment_score > 0.6 ? "#EF4444" : "#10B981"} />
            <StatCard label="Litigation Count" value={res.litigation_count || 0} color="#EF4444" />
            <StatCard label="Regulatory Violations" value={res.regulatory_violation_count || 0} color="#F59E0B" />
          </div>

          {(res.articles || []).length > 0 && (
            <SectionCard title="News Articles" color="#0EA5E9" icon="📰">
              {res.articles.map((a, i) => (
                <div key={i} style={{
                  padding: "8px 12px", borderRadius: 10, marginBottom: 6,
                  background: a.sentiment === "NEGATIVE" ? "rgba(239,68,68,.06)" : a.sentiment === "POSITIVE" ? "rgba(16,185,129,.06)" : "rgba(0,0,0,.02)",
                  borderLeft: `3px solid ${a.sentiment === "NEGATIVE" ? "#EF4444" : a.sentiment === "POSITIVE" ? "#10B981" : "#94A3B8"}`,
                }}>
                  <p style={{ fontSize: 11, color: "#334155", fontWeight: 600, marginBottom: 2 }}>{a.title || a.url}</p>
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                    background: a.sentiment === "NEGATIVE" ? "#FEE2E2" : a.sentiment === "POSITIVE" ? "#DCFCE7" : "#F1F5F9",
                    color: a.sentiment === "NEGATIVE" ? "#DC2626" : a.sentiment === "POSITIVE" ? "#059669" : "#64748B",
                  }}>{a.sentiment}</span>
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
              ? verif.gst_bank.flags.map((f, i) => <FlagItem key={i} text={f} color="#F59E0B" />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No GST-bank mismatches.</p>}
          </SectionCard>

          <SectionCard title="ITR Cross-check" color="#F59E0B" icon="📋">
            {(verif.itr?.flags || []).length > 0
              ? verif.itr.flags.map((f, i) => <FlagItem key={i} text={f} color="#F59E0B" />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No ITR mismatches.</p>}
          </SectionCard>

          <SectionCard title="GSTR-2A vs 3B" color="#EF4444" icon="⚠">
            {(verif.gstr2a_3b?.flags || []).length > 0
              ? verif.gstr2a_3b.flags.map((f, i) => <FlagItem key={i} text={f} color="#EF4444" />)
              : <p style={{ fontSize: 11, color: "#94A3B8", fontStyle: "italic" }}>No GSTR-2A/3B mismatches.</p>}
          </SectionCard>
        </div>
      )}
    </div>
  );
}
