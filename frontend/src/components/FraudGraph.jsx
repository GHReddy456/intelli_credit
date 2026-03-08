import React from "react";

function StatCard({ icon, label, value, color }) {
  return (
    <div className="glass" style={{ padding: "16px 18px", borderRadius: 16, borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 20, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 24, fontWeight: 900, color }}>{value}</div>
      <div style={{ fontSize: 9, color: "#64748B", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginTop: 3 }}>{label}</div>
    </div>
  );
}

function DigitBar({ digit, actual, expected, maxVal }) {
  const aPct = maxVal > 0 ? (actual / maxVal) * 100 : 0;
  const ePct = maxVal > 0 ? (expected / maxVal) * 100 : 0;
  const diff = expected > 0 ? Math.abs(actual - expected) / expected : 0;
  const color = diff > 0.3 ? "#EF4444" : diff > 0.15 ? "#F59E0B" : "#10B981";
  return (
    <div style={{ marginBottom: 7 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "#475569" }}>Digit {digit}</span>
        <span style={{ fontSize: 10, color }}>{actual} observed / {expected} expected</span>
      </div>
      <div style={{ height: 10, borderRadius: 6, background: "#F1F5F9", position: "relative", overflow: "visible" }}>
        <div style={{ height: "100%", width: `${aPct}%`, background: color, borderRadius: 6, transition: "width 0.9s ease" }} />
        <div style={{ position: "absolute", top: -3, left: `${ePct}%`, width: 2, height: 16, background: "#0891b2", opacity: 0.8 }} />
      </div>
    </div>
  );
}

export default function FraudGraph({ analysis }) {
  const gdata = analysis?.fraud_graph || { nodes: [], links: [], stats: {} };
  const fraud = analysis?.fraud       || {};

  const score      = parseFloat(fraud.fraud_risk_score || 0);
  const scoreColor = score <= 25 ? "#10B981" : score <= 55 ? "#F59E0B" : "#EF4444";
  const scoreBg    = score <= 25 ? "#F0FDF4" : score <= 55 ? "#FFFBEB"  : "#FEF2F2";
  const scoreLabel = score <= 25 ? "LOW RISK" : score <= 55 ? "MEDIUM RISK" : "HIGH RISK";

  const benford    = fraud.benford || {};
  const digCounts  = benford.digit_counts   || {};
  const expCounts  = benford.expected_counts || {};
  const digits     = [1,2,3,4,5,6,7,8,9];
  const maxVal     = Math.max(1, ...digits.map(d => digCounts[d] || 0));

  const flags      = fraud.flags    || [];
  const allNodes   = gdata.nodes    || [];
  const suspNodes  = allNodes.filter(n => n.inCycle || n.suspicious || n.flagged);
  const cycleCount = gdata.stats?.cycle_count  || 0;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }} className="fade-in-up">

      {/* ── Hero row ─────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 16, marginBottom: 20 }}>
        <div style={{
          background: scoreBg, border: `3px solid ${scoreColor}`, borderRadius: 20,
          padding: "28px 20px", textAlign: "center", boxShadow: `0 8px 30px ${scoreColor}30`,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#64748B", letterSpacing: "1px", marginBottom: 6, textTransform: "uppercase" }}>Fraud Risk Score</div>
          <div style={{ fontSize: 56, fontWeight: 900, color: scoreColor, lineHeight: 1 }}>{score.toFixed(0)}</div>
          <div style={{ fontSize: 11, color: "#94A3B8", marginBottom: 10 }}>/100</div>
          <div style={{ display: "inline-block", padding: "4px 14px", borderRadius: 20, background: `${scoreColor}20`, color: scoreColor, fontSize: 11, fontWeight: 800 }}>
            {scoreLabel}
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
          <StatCard icon="🔄" label="Circular Cycles"       value={cycleCount}                      color={cycleCount > 0 ? "#EF4444" : "#10B981"} />
          <StatCard icon="⚠️" label="Suspicious Entities"   value={suspNodes.length}                color={suspNodes.length > 0 ? "#EF4444" : "#10B981"} />
          <StatCard icon="🏢" label="Total Entities Mapped"  value={allNodes.length || gdata.stats?.total_nodes || 0} color="#36cceb" />
          <StatCard icon="📊" label="Chi² Anomaly Score"     value={benford.chi2 != null ? parseFloat(benford.chi2).toFixed(1) : "—"} color={(benford.chi2||0)>20?"#EF4444":"#10B981"} />
          <StatCard icon="📈" label="Benford Fraud Score"    value={benford.benford_score != null ? `${(benford.benford_score*100).toFixed(0)}%` : "—"} color={(benford.benford_score||0)>0.7?"#EF4444":"#10B981"} />
          <StatCard icon="🚩" label="Fraud Flags"            value={flags.length}                    color={flags.length > 0 ? "#F59E0B" : "#10B981"} />
        </div>
      </div>

      {fraud.summary && (
        <div className="glass" style={{ padding: "14px 18px", borderRadius: 14, marginBottom: 16, borderLeft: `4px solid ${scoreColor}`, background: scoreBg }}>
          <span style={{ fontSize: 13, color: "#334155", fontStyle: "italic" }}>{fraud.summary}</span>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Benford analysis */}
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#0891b2", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 4 }}>📊 Benford's Law — Digit Analysis</h3>
          <p style={{ fontSize: 10, color: "#94A3B8", marginBottom: 14 }}>Blue line = Benford expected. Colored bars = actual. Red bars signal digit manipulation.</p>
          {Object.keys(digCounts).length > 0 ? (
            <>
              {digits.map(d => <DigitBar key={d} digit={d} actual={digCounts[d]||0} expected={Math.round(expCounts[d]||0)} maxVal={maxVal} />)}
              {benford.chi2 != null && (
                <div style={{ marginTop: 12, padding: "9px 14px", borderRadius: 10, background: (benford.benford_score||0)>0.7?"#FEF2F2":"#F0FDF4", border: `1px solid ${(benford.benford_score||0)>0.7?"#FECACA":"#BBF7D0"}` }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: (benford.benford_score||0)>0.7?"#EF4444":"#059669" }}>
                    {(benford.benford_score||0)>0.7 ? "⚠ Significant digit anomaly — possible manipulation of financial figures" : "✓ Digit distribution is within the expected Benford range"}
                  </span>
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "28px 0", color: "#94A3B8" }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>📉</div>
              <div style={{ fontSize: 12 }}>Benford analysis requires transaction data.<br/>Upload bank statements to enable.</div>
            </div>
          )}
        </div>

        {/* Fraud flags */}
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#EF4444", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 16 }}>🚩 Fraud Flags &amp; Warnings</h3>
          {flags.length > 0 ? flags.map((f, i) => {
            const sev = (f.severity||"INFO").toUpperCase();
            const c   = sev==="HIGH"?"#EF4444":sev==="MEDIUM"?"#F59E0B":"#10B981";
            const bg  = sev==="HIGH"?"#FEF2F2":sev==="MEDIUM"?"#FFFBEB":"#F0FDF4";
            return (
              <div key={i} style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8, background: bg, borderLeft: `4px solid ${c}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#1E293B" }}>{f.flag||f.type||f.name||"Flag"}</span>
                  <span style={{ fontSize: 9, fontWeight: 800, padding: "2px 10px", borderRadius: 10, background: c, color: "white" }}>{sev}</span>
                </div>
                <span style={{ fontSize: 10, color: "#475569" }}>{f.message||f.detail||f.description||""}</span>
              </div>
            );
          }) : (
            <div style={{ padding: "32px 0", textAlign: "center", background: "#F0FDF4", borderRadius: 12 }}>
              <div style={{ fontSize: 36, marginBottom: 8 }}>✅</div>
              <div style={{ fontWeight: 700, color: "#059669", fontSize: 14 }}>No Fraud Flags Detected</div>
              <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 4 }}>Transaction patterns appear normal</div>
            </div>
          )}
        </div>
      </div>

      {/* Suspicious entities table */}
      {suspNodes.length > 0 && (
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18, marginBottom: 16 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, color: "#EF4444", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 14 }}>⚠ Suspicious Entities</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#FEF2F2" }}>
                {["Entity","Type","In Cycle","Risk Reason"].map(h=>(
                  <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontWeight:700, fontSize:10, color:"#EF4444", letterSpacing:"0.5px", borderBottom:"2px solid #FECACA" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suspNodes.map((n,i)=>(
                <tr key={i} style={{ borderBottom:"1px solid #F1F5F9", background:i%2===0?"#FFFBFB":"#FFFFFF" }}>
                  <td style={{ padding:"9px 14px", fontWeight:600, color:"#1E293B" }}>{n.label||n.id}</td>
                  <td style={{ padding:"9px 14px", color:"#475569" }}>{n.type||"Entity"}</td>
                  <td style={{ padding:"9px 14px" }}>
                    <span style={{ padding:"2px 10px", borderRadius:10, fontSize:10, fontWeight:700, background:n.inCycle?"#FEE2E2":"#F0FDF4", color:n.inCycle?"#EF4444":"#059669" }}>
                      {n.inCycle?"YES":"No"}
                    </span>
                  </td>
                  <td style={{ padding:"9px 14px", color:"#EF4444", fontSize:10 }}>{n.reason||n.riskReason||"Anomalous pattern detected"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Circular chains */}
      {(gdata.cycle_summaries||[]).length > 0 && (
        <div className="glass" style={{ padding:"20px 20px", borderRadius:18, marginBottom:16 }}>
          <h3 style={{ fontSize:11, fontWeight:700, color:"#EF4444", letterSpacing:"1px", textTransform:"uppercase", marginBottom:14 }}>🔄 Circular Trading Chains Detected</h3>
          {gdata.cycle_summaries.slice(0,10).map((c,i)=>(
            <div key={i} style={{ padding:"10px 14px", borderRadius:10, marginBottom:8, background:"#FFF5F5", borderLeft:"4px solid #EF4444" }}>
              <span style={{ fontSize:11, color:"#334155", fontFamily:"monospace" }}>{c.description||(c.nodes||[]).join(" → ")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Clean bill */}
      {!suspNodes.length && !flags.length && cycleCount===0 && (
        <div className="glass" style={{ padding:"36px", borderRadius:20, textAlign:"center", border:"2px solid #10B981", background:"#F0FDF4" }}>
          <div style={{ fontSize:52, marginBottom:12 }}>✅</div>
          <div style={{ fontSize:18, fontWeight:800, color:"#059669", marginBottom:8 }}>Clean Fraud Assessment</div>
          <div style={{ fontSize:13, color:"#64748B" }}>No circular trading, no Benford anomalies, and no suspicious entities were detected during this analysis.</div>
        </div>
      )}
    </div>
  );
}
