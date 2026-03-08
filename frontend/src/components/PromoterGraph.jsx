import React, { useState } from "react";

/* ─── type colour map ───────────────────────────── */
const TYPE_COLOR = {
  Promoter:  { bg: "#EFF6FF", border: "#2563EB", dot: "#2563EB" },
  Director:  { bg: "#F0FDF4", border: "#059669", dot: "#059669" },
  Company:   { bg: "#F0F9FF", border: "#0891b2", dot: "#0891b2" },
  Litigation:{ bg: "#FEF2F2", border: "#EF4444", dot: "#EF4444" },
  Lender:    { bg: "#FAF5FF", border: "#7C3AED", dot: "#7C3AED" },
};

function getTypeStyle(type) {
  return TYPE_COLOR[type] || { bg: "#F8FAFC", border: "#94A3B8", dot: "#94A3B8" };
}

function DirectorCard({ node }) {
  const [open, setOpen] = useState(false);
  const st = getTypeStyle(node.type);
  return (
    <div
      style={{
        background: st.bg, border: `1.5px solid ${st.border}40`,
        borderLeft: `4px solid ${st.border}`, borderRadius: 14,
        padding: "14px 16px", cursor: "pointer",
        boxShadow: "0 2px 8px rgba(0,0,0,.05)",
        transition: "box-shadow .2s",
      }}
      onClick={() => setOpen(!open)}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 38, height: 38, borderRadius: "50%", background: st.border, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 14, fontWeight: 800, flexShrink: 0 }}>
          {(node.label || node.id || "?").charAt(0).toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#1E293B", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{node.label || node.id}</div>
          <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
            <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 8px", borderRadius: 8, background: st.border, color: "#fff" }}>{node.type || "Entity"}</span>
            {node.inCycle && <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 8px", borderRadius: 8, background: "#EF4444", color: "#fff" }}>⚠ In Cycle</span>}
            {node.litigations > 0 && <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 8px", borderRadius: 8, background: "#F59E0B", color: "#fff" }}>⚖ {node.litigations} case{node.litigations>1?"s":""}</span>}
          </div>
        </div>
        <div style={{ fontSize: 16, color: "#94A3B8" }}>{open ? "▲" : "▼"}</div>
      </div>

      {open && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px dashed ${st.border}40` }}>
          {node.din && <div style={{ fontSize: 11, color: "#475569", marginBottom: 3 }}><strong>DIN:</strong> {node.din}</div>}
          {node.designation && <div style={{ fontSize: 11, color: "#475569", marginBottom: 3 }}><strong>Designation:</strong> {node.designation}</div>}
          {node.riskScore != null && <div style={{ fontSize: 11, color: "#475569", marginBottom: 3 }}><strong>Risk Score:</strong> {parseFloat(node.riskScore).toFixed(3)}</div>}
          {node.entities?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 6 }}>Related Entities</div>
              {node.entities.map((e, ei) => (
                <div key={ei} style={{ fontSize: 10, color: "#334155", padding: "3px 8px", borderRadius: 6, background: "#FFFFFF", marginBottom: 3, border: "1px solid #E2E8F0" }}>{e}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function PromoterGraph({ analysis }) {
  const gdata = analysis?.promoter_graph || { nodes: [], links: [], stats: {} };
  const pdata = analysis?.promoter       || {};

  const netRisk    = parseFloat(pdata.promoter_network_risk || 0);
  const riskColor  = netRisk <= 0.25 ? "#10B981" : netRisk <= 0.6 ? "#F59E0B" : "#EF4444";
  const promoterCount  = gdata.stats?.promoter_count  || 0;
  const litigCount     = gdata.stats?.litigation_count || 0;
  const totalCount     = gdata.stats?.total_nodes      || gdata.nodes?.length || 0;

  const nodes     = gdata.nodes || [];
  const directors = pdata.directors || [];

  /* Group nodes by type for the entity table */
  const entityGroups = nodes.reduce((acc, n) => {
    const t = n.type || "Other";
    if (!acc[t]) acc[t] = [];
    acc[t].push(n);
    return acc;
  }, {});

  /* Litigations from pdata */
  const litigations = pdata.litigations || [];

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }} className="fade-in-up">

      {/* ── Summary stats ──────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 20 }}>
        {[
          { icon: "🔐", label: "Network Risk Score", value: netRisk.toFixed(3), color: riskColor },
          { icon: "👥", label: "Promoters / Directors", value: promoterCount, color: "#0891b2" },
          { icon: "⚖️", label: "Litigation Count", value: litigCount, color: litigCount > 0 ? "#EF4444" : "#10B981" },
          { icon: "🏢", label: "Total Entities", value: totalCount, color: "#8B5CF6" },
        ].map(m => (
          <div key={m.label} className="glass" style={{ padding: "18px 16px", borderRadius: 16, borderLeft: `4px solid ${m.color}`, textAlign: "left" }}>
            <div style={{ fontSize: 22, marginBottom: 4 }}>{m.icon}</div>
            <div style={{ fontSize: 26, fontWeight: 900, color: m.color }}>{m.value}</div>
            <div style={{ fontSize: 9, color: "#64748B", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginTop: 3 }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* ── narrative summaries ─────────────────────────── */}
      {(pdata.network_summary || pdata.litigation_summary) && (
        <div style={{ display: "grid", gridTemplateColumns: pdata.network_summary && pdata.litigation_summary ? "1fr 1fr" : "1fr", gap: 14, marginBottom: 16 }}>
          {pdata.network_summary && (
            <div className="glass" style={{ padding: "14px 18px", borderRadius: 14, borderLeft: "4px solid #0891b2", background: "#F0F9FF" }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: "#0891b2", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 6 }}>Network Summary</div>
              <div style={{ fontSize: 12, color: "#334155", lineHeight: 1.6 }}>{pdata.network_summary}</div>
            </div>
          )}
          {pdata.litigation_summary && (
            <div className="glass" style={{ padding: "14px 18px", borderRadius: 14, borderLeft: "4px solid #EF4444", background: "#FEF2F2" }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: "#EF4444", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 6 }}>Litigation Summary</div>
              <div style={{ fontSize: 12, color: "#334155", lineHeight: 1.6 }}>{pdata.litigation_summary}</div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* ── Director/promoter cards ─────────────────── */}
        <div className="glass" style={{ padding: "20px 18px", borderRadius: 18 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#0891b2", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 14 }}>👥 Promoters &amp; Directors</h3>
          {(directors.length > 0 ? directors : nodes.filter(n => n.type === "Promoter" || n.type === "Director")).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {(directors.length > 0 ? directors : nodes.filter(n => n.type === "Promoter" || n.type === "Director")).map((d, i) => (
                <DirectorCard key={i} node={{ ...d, label: d.name || d.label || d.id }} />
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "28px 0", color: "#94A3B8" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>👥</div>
              <div style={{ fontSize: 12 }}>No director/promoter data extracted.<br/>Upload MCA filings for this analysis.</div>
            </div>
          )}
        </div>

        {/* ── Litigation cases ───────────────────────── */}
        <div className="glass" style={{ padding: "20px 18px", borderRadius: 18 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#EF4444", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 14 }}>⚖️ Litigation Cases</h3>
          {litigations.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {litigations.map((l, i) => {
                const sev = (l.severity || "MEDIUM").toUpperCase();
                const c   = sev === "HIGH" ? "#EF4444" : sev === "MEDIUM" ? "#F59E0B" : "#10B981";
                const bg  = sev === "HIGH" ? "#FEF2F2" : sev === "MEDIUM" ? "#FFFBEB" : "#F0FDF4";
                return (
                  <div key={i} style={{ padding: "12px 14px", borderRadius: 12, background: bg, borderLeft: `4px solid ${c}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "#1E293B" }}>{l.case_title || l.title || l.case_number || `Case #${i+1}`}</span>
                      <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 8px", borderRadius: 8, background: c, color: "#fff", flexShrink: 0, marginLeft: 8 }}>{sev}</span>
                    </div>
                    {l.court && <div style={{ fontSize: 10, color: "#475569", marginBottom: 3 }}>🏛 {l.court}</div>}
                    {l.status && <div style={{ fontSize: 10, color: "#475569" }}>Status: <strong>{l.status}</strong></div>}
                    {l.description && <div style={{ fontSize: 10, color: "#64748B", marginTop: 6, fontStyle: "italic" }}>{l.description}</div>}
                  </div>
                );
              })}
            </div>
          ) : litigCount > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {nodes.filter(n => n.type === "Litigation").map((l, i) => (
                <div key={i} style={{ padding: "10px 14px", borderRadius: 10, background: "#FEF2F2", borderLeft: "4px solid #EF4444" }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#1E293B" }}>{l.label || l.id}</div>
                  {l.riskScore && <div style={{ fontSize: 10, color: "#EF4444", marginTop: 3 }}>Risk Score: {parseFloat(l.riskScore).toFixed(3)}</div>}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "28px 0", background: "#F0FDF4", borderRadius: 12 }}>
              <div style={{ fontSize: 36, marginBottom: 8 }}>✅</div>
              <div style={{ fontWeight: 700, color: "#059669", fontSize: 14 }}>No Litigations Found</div>
              <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 4 }}>Clean legal record for all promoters</div>
            </div>
          )}
        </div>
      </div>

      {/* ── Entity table ─────────────────────────────── */}
      {Object.keys(entityGroups).length > 0 && (
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 14 }}>🏢 Full Entity Network Breakdown</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#F8FAFC" }}>
                {["Entity","Type","Risk Score","In Cycle"].map(h => (
                  <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontWeight: 700, fontSize: 10, color: "#475569", letterSpacing: "0.5px", borderBottom: "2px solid #E2E8F0" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {nodes.map((n, i) => {
                const st = getTypeStyle(n.type);
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #F1F5F9", background: i%2===0?"#FAFCFF":"#FFFFFF" }}>
                    <td style={{ padding: "9px 14px", fontWeight: 600, color: "#1E293B" }}>{n.label || n.id}</td>
                    <td style={{ padding: "9px 14px" }}>
                      <span style={{ padding: "2px 10px", borderRadius: 8, fontSize: 10, fontWeight: 700, background: st.bg, color: st.border, border: `1px solid ${st.border}40` }}>{n.type || "Entity"}</span>
                    </td>
                    <td style={{ padding: "9px 14px", color: n.riskScore > 0.7 ? "#EF4444" : "#10B981", fontWeight: 700 }}>
                      {n.riskScore != null ? parseFloat(n.riskScore).toFixed(3) : "—"}
                    </td>
                    <td style={{ padding: "9px 14px" }}>
                      <span style={{ padding: "2px 10px", borderRadius: 8, fontSize: 10, fontWeight: 700, background: n.inCycle?"#FEE2E2":"#F0FDF4", color: n.inCycle?"#EF4444":"#059669" }}>
                        {n.inCycle?"YES":"No"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {nodes.length === 0 && directors.length === 0 && (
        <div className="glass" style={{ padding: "36px", borderRadius: 20, textAlign: "center", border: "2px dashed #CBD5E1" }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔗</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: "#64748B", marginBottom: 8 }}>No Network Data Available</div>
          <div style={{ fontSize: 13, color: "#94A3B8" }}>Upload MCA/ROC filings to build the promoter network map.</div>
        </div>
      )}
    </div>
  );
}

export { getTypeStyle };
