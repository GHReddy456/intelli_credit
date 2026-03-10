import React, { useRef, useEffect, useState } from "react";
import * as d3 from "d3";

/* ── D3 Force-Directed Network Graph ──────────────────────────────────────── */
function NetworkGraph({ nodes = [], links = [] }) {
  const svgRef  = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [dims,    setDims]    = useState({ w: 800, h: 440 });

  // Responsive: measure container
  useEffect(() => {
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const obs = new ResizeObserver(entries => {
      const w = entries[0].contentRect.width;
      setDims({ w: Math.max(w, 400), h: Math.max(Math.round(w * 0.52), 320) });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current) return;
    const { w, h } = dims;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${w} ${h}`);

    if (!nodes.length) return;

    // Deep-copy so D3 mutation doesn't affect React props
    const simNodes = nodes.map(n => ({ ...n }));
    const idSet    = new Set(simNodes.map(n => n.id));
    const simLinks = links
      .filter(l => idSet.has(l.source) && idSet.has(l.target))
      .map(l => ({ ...l }));

    // Color by node type
    const nodeColor = n => {
      if (n.id === "SELF")   return "#0ea5e9";  // applicant — sky blue
      if (n.inCycle)         return "#EF4444";  // cycle     — red
      if (n.isShell)         return "#F59E0B";  // shell     — amber
      if (n.suspicious)      return "#F97316";  // other suspicious — orange
      return "#64748B";                          // normal    — slate
    };

    // Background
    svg.append("rect").attr("width", w).attr("height", h)
      .attr("fill", "#0F172A").attr("rx", 14);

    // Arrowhead defs
    const defs = svg.append("defs");
    ["cycle","normal","layered"].forEach(type => {
      defs.append("marker")
        .attr("id",          `fg-arrow-${type}`)
        .attr("viewBox",     "0 -5 10 10")
        .attr("refX",        22)
        .attr("refY",        0)
        .attr("markerWidth", 5)
        .attr("markerHeight",5)
        .attr("orient",      "auto")
        .append("path")
        .attr("d",    "M0,-5L10,0L0,5")
        .attr("fill", type === "cycle" ? "#EF4444" : type === "layered" ? "#F59E0B" : "#475569");
    });

    // Grid dots (subtle background texture)
    for (let gx = 30; gx < w; gx += 40)
      for (let gy = 30; gy < h; gy += 40)
        svg.append("circle").attr("cx", gx).attr("cy", gy).attr("r", 0.8).attr("fill", "#1E293B");

    // Force simulation
    const sim = d3.forceSimulation(simNodes)
      .force("link",      d3.forceLink(simLinks).id(d => d.id).distance(100).strength(0.6))
      .force("charge",    d3.forceManyBody().strength(-280))
      .force("center",    d3.forceCenter(w / 2, h / 2))
      .force("collision", d3.forceCollide().radius(d => (d.radius || 8) + 14));

    // Links
    const linkSel = svg.append("g").attr("class", "links")
      .selectAll("line").data(simLinks).enter().append("line")
      .attr("stroke",       d => d.isCycle ? "#EF4444" : d.isLayered ? "#F59E0B80" : "#33415550")
      .attr("stroke-width", d => d.isCycle ? 2.5 : d.isLayered ? 1.8 : 1.2)
      .attr("stroke-dasharray", d => d.isLayered ? "6,4" : null)
      .attr("marker-end",   d => `url(#fg-arrow-${d.isCycle ? "cycle" : d.isLayered ? "layered" : "normal"})`);

    // Glow rings for suspicious nodes
    const nodeG = svg.append("g").attr("class", "nodes")
      .selectAll("g").data(simNodes).enter().append("g")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag",  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on("end",   (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    // Outer glow (pulse) for flagged nodes
    nodeG.filter(n => n.inCycle || n.isShell || n.suspicious)
      .append("circle")
      .attr("r",       d => (d.radius || 8) + 8)
      .attr("fill",    d => nodeColor(d))
      .attr("opacity", 0.18);

    // Main node circle
    nodeG.append("circle")
      .attr("r",            d => d.radius || 8)
      .attr("fill",         d => nodeColor(d))
      .attr("stroke",       "#0F172A")
      .attr("stroke-width", 2)
      .on("mouseenter", (ev, d) => setTooltip({ x: ev.clientX, y: ev.clientY, node: d }))
      .on("mouseleave", ()      => setTooltip(null));

    // Node icon for SELF
    nodeG.filter(n => n.id === "SELF")
      .append("text")
      .attr("text-anchor",     "middle")
      .attr("dominant-baseline","central")
      .attr("font-size",        11)
      .attr("pointer-events",   "none")
      .text("🏢");

    // Labels (clipped)
    nodeG.append("text")
      .attr("dy",              d => (d.radius || 8) + 13)
      .attr("text-anchor",     "middle")
      .attr("font-size",       8.5)
      .attr("font-weight",     600)
      .attr("fill",            d => nodeColor(d))
      .attr("pointer-events",  "none")
      .text(d => (d.id === "SELF" ? "" : (d.label || d.id || "").slice(0, 20)));

    // Tick
    sim.on("tick", () => {
      const clampX = x => Math.max(20, Math.min(w - 20, x));
      const clampY = y => Math.max(20, Math.min(h - 20, y));
      linkSel
        .attr("x1", d => clampX(d.source.x))
        .attr("y1", d => clampY(d.source.y))
        .attr("x2", d => clampX(d.target.x))
        .attr("y2", d => clampY(d.target.y));
      nodeG.attr("transform", d => `translate(${clampX(d.x)},${clampY(d.y)})`);
    });

    return () => sim.stop();
  }, [nodes, links, dims]);

  return (
    <div style={{ position: "relative" }}>
      <svg ref={svgRef} style={{ width: "100%", height: dims.h, display: "block", borderRadius: 14 }} />

      {/* Legend */}
      <div style={{ position: "absolute", top: 12, right: 14, display: "flex", flexDirection: "column", gap: 5 }}>
        {[
          { color: "#0ea5e9", label: "Applicant" },
          { color: "#EF4444", label: "Circular Cycle" },
          { color: "#F59E0B", label: "Shell Entity" },
          { color: "#F97316", label: "Suspicious" },
          { color: "#64748B", label: "Counterparty" },
        ].map(item => (
          <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: item.color }} />
            <span style={{ fontSize:15, color: "#94A3B8", fontWeight: 600 }}>{item.label}</span>
          </div>
        ))}
        <div style={{ marginTop: 4, borderTop: "1px solid #1E293B", paddingTop: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 18, height: 2, background: "#EF4444" }} />
            <span style={{ fontSize:15, color: "#94A3B8" }}>Cycle edge</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
            <div style={{ width: 18, height: 2, background: "#F59E0B", opacity: 0.7, borderTop: "2px dashed" }} />
            <span style={{ fontSize:15, color: "#94A3B8" }}>Layered</span>
          </div>
        </div>
      </div>

      <div style={{ position: "absolute", bottom: 10, left: 14, fontSize:14, color: "#475569" }}>
        Drag nodes • Hover for detail • Arrows = money flow direction
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: "fixed", left: tooltip.x + 14, top: tooltip.y - 14,
          pointerEvents: "none", background: "#1E293B",
          border: "1px solid #334155", borderRadius: 10,
          padding: "9px 13px", fontSize:17, color: "#E2E8F0",
          zIndex: 9999, maxWidth: 240,
          boxShadow: "0 8px 28px rgba(0,0,0,0.5)",
        }}>
          <div style={{ fontWeight: 800, marginBottom: 5, color:
            tooltip.node.id === "SELF"  ? "#0ea5e9"
            : tooltip.node.inCycle      ? "#EF4444"
            : tooltip.node.isShell      ? "#F59E0B"
            : tooltip.node.suspicious   ? "#F97316" : "#94A3B8"
          }}>
            {tooltip.node.label || tooltip.node.id}
          </div>
          {tooltip.node.txCount > 0 && (
            <div style={{ color: "#94A3B8" }}>Transactions: <b style={{ color: "#E2E8F0" }}>{tooltip.node.txCount}</b></div>
          )}
          {tooltip.node.inCycle && (
            <div style={{ color: "#EF4444", marginTop: 4, fontWeight: 700 }}>⚠ In Circular Cycle</div>
          )}
          {tooltip.node.isShell && (
            <div style={{ color: "#F59E0B", marginTop: 4, fontWeight: 700 }}>⚠ Potential Shell Entity</div>
          )}
          {tooltip.node.reason && (
            <div style={{ color: "#64748B", marginTop: 4, fontStyle: "italic", fontSize:16 }}>
              {tooltip.node.reason}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Stat card shared sub-component ──────────────────────────────────────── */
function StatCard({ icon, label, value, color }) {
  return (
    <div className="glass" style={{ padding: "16px 18px", borderRadius: 16, borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize:23, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize:27, fontWeight: 900, color }}>{value}</div>
      <div style={{ fontSize:15, color: "#64748B", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginTop: 3 }}>{label}</div>
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
        <span style={{ fontSize:16, fontWeight: 700, color: "#475569" }}>Digit {digit}</span>
        <span style={{ fontSize:16, color }}>{actual} observed / {expected} expected</span>
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
  const scoreColor = score < 20 ? "#10B981" : score < 40 ? "#F59E0B" : score < 70 ? "#EF4444" : "#991B1B";
  const scoreBg    = score < 20 ? "#F0FDF4" : score < 40 ? "#FFFBEB"  : score < 70 ? "#FEF2F2" : "#FEF2F2";
  const scoreLabel = score < 20 ? "LOW RISK" : score < 40 ? "MODERATE RISK" : score < 70 ? "HIGH RISK" : "SEVERE RISK";

  const benford    = fraud.benford || {};
  const digCounts  = benford.digit_counts   || {};
  const expCounts  = benford.expected_counts || {};
  const digits     = [1,2,3,4,5,6,7,8,9];
  const maxVal     = Math.max(1, ...digits.map(d => digCounts[d] || 0));

  const flags      = fraud.all_flags || fraud.flags || [];
  const allNodes   = gdata.nodes    || [];
  const suspNodes  = allNodes.filter(n => n.inCycle || n.suspicious || n.flagged);
  const cycleCount = gdata.stats?.cycle_count  || 0;

  return (
    <div className="fade-in-up">

      {/* ── Hero row ─────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 16, marginBottom: 20 }}>
        <div style={{
          background: scoreBg, border: `3px solid ${scoreColor}`, borderRadius: 20,
          padding: "28px 20px", textAlign: "center", boxShadow: `0 8px 30px ${scoreColor}30`,
        }}>
          <div style={{ fontSize:16, fontWeight: 700, color: "#64748B", letterSpacing: "1px", marginBottom: 6, textTransform: "uppercase" }}>Fraud Risk Score</div>
          <div style={{ fontSize:58, fontWeight: 900, color: scoreColor, lineHeight: 1 }}>{score.toFixed(0)}</div>
          <div style={{ fontSize:17, color: "#94A3B8", marginBottom: 10 }}>/100</div>
          <div style={{ display: "inline-block", padding: "4px 14px", borderRadius: 20, background: `${scoreColor}20`, color: scoreColor, fontSize:17, fontWeight: 800 }}>
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
          <span style={{ fontSize:19, color: "#334155", fontStyle: "italic" }}>{fraud.summary}</span>
        </div>
      )}

      {/* ── D3 Network Graph ─────────────────────────────── */}
      <div className="glass" style={{ padding: "20px 20px", borderRadius: 18, marginBottom: 16 }}>
        <h3 style={{ fontSize:17, fontWeight: 700, color: "#36cceb", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 4 }}>
          🕸 Counterparty Transaction Network
        </h3>
        <p style={{ fontSize:16, color: "#94A3B8", marginBottom: 14 }}>
          Force-directed graph of transaction relationships. Red = circular cycle node · Amber = shell entity · Drag nodes to explore.
        </p>
        {(gdata.nodes || []).length > 1 ? (
          <NetworkGraph nodes={gdata.nodes} links={gdata.links} />
        ) : (
          <div style={{ textAlign: "center", padding: "48px 0", background: "#0F172A", borderRadius: 14, color: "#94A3B8" }}>
            <div style={{ fontSize:43, marginBottom: 12 }}>📡</div>
            <div style={{ fontSize:19, fontWeight: 600, color: "#475569" }}>No counterparty network data</div>
            <div style={{ fontSize:17, marginTop: 6 }}>Upload bank statements to visualize transaction flows</div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Benford analysis */}
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18 }}>
          <h3 style={{ fontSize:17, fontWeight: 700, color: "#0891b2", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 4 }}>📊 Benford's Law — Digit Analysis</h3>
          <p style={{ fontSize:16, color: "#94A3B8", marginBottom: 14 }}>Blue line = Benford expected. Colored bars = actual. Red bars signal digit manipulation.</p>
          {Object.keys(digCounts).length > 0 ? (
            <>
              {digits.map(d => <DigitBar key={d} digit={d} actual={digCounts[d]||0} expected={Math.round(expCounts[d]||0)} maxVal={maxVal} />)}
              {benford.chi2 != null && (
                <div style={{ marginTop: 12, padding: "9px 14px", borderRadius: 10, background: (benford.benford_score||0)>0.7?"#FEF2F2":"#F0FDF4", border: `1px solid ${(benford.benford_score||0)>0.7?"#FECACA":"#BBF7D0"}` }}>
                  <span style={{ fontSize:16, fontWeight: 700, color: (benford.benford_score||0)>0.7?"#EF4444":"#059669" }}>
                    {(benford.benford_score||0)>0.7 ? "⚠ Significant digit anomaly — possible manipulation of financial figures" : "✓ Digit distribution is within the expected Benford range"}
                  </span>
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "28px 0", color: "#94A3B8" }}>
              <div style={{ fontSize:32, marginBottom: 10 }}>📉</div>
              <div style={{ fontSize:15 }}>
                {benford.status === "insufficient_data"
                  ? (benford.message || `Insufficient transaction data for Benford analysis (${benford.sample_size || 0} of 100 required)`)
                  : "Benford analysis requires transaction data. Upload bank statements to enable."}
              </div>
            </div>
          )}
        </div>

        {/* Fraud flags */}
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18 }}>
          <h3 style={{ fontSize:17, fontWeight: 700, color: "#EF4444", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 16 }}>🚩 Fraud Flags &amp; Warnings</h3>
          {flags.length > 0 ? flags.map((f, i) => {
            const sev = (f.severity||"INFO").toUpperCase();
            const c   = sev==="HIGH"?"#EF4444":sev==="MEDIUM"?"#F59E0B":"#10B981";
            const bg  = sev==="HIGH"?"#FEF2F2":sev==="MEDIUM"?"#FFFBEB":"#F0FDF4";
            return (
              <div key={i} style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 8, background: bg, borderLeft: `4px solid ${c}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                  <span style={{ fontSize:17, fontWeight: 700, color: "#1E293B" }}>{f.flag||f.type||f.name||"Flag"}</span>
                  <span style={{ fontSize:15, fontWeight: 800, padding: "2px 10px", borderRadius: 10, background: c, color: "white" }}>{sev}</span>
                </div>
                <span style={{ fontSize:16, color: "#475569" }}>{f.message||f.detail||f.description||""}</span>
              </div>
            );
          }) : (
            <div style={{ padding: "32px 0", textAlign: "center", background: "#F0FDF4", borderRadius: 12 }}>
              <div style={{ fontSize:39, marginBottom: 8 }}>✅</div>
              <div style={{ fontWeight: 700, color: "#059669", fontSize:17 }}>No Fraud Flags Detected</div>
              <div style={{ fontSize:17, color: "#94A3B8", marginTop: 4 }}>Transaction patterns appear normal</div>
            </div>
          )}
        </div>
      </div>

      {/* Suspicious entities table */}
      {suspNodes.length > 0 && (
        <div className="glass" style={{ padding: "20px 20px", borderRadius: 18, marginBottom: 16 }}>
          <h3 style={{ fontSize:17, fontWeight: 700, color: "#EF4444", letterSpacing: "1px", textTransform: "uppercase", marginBottom: 14 }}>⚠ Suspicious Entities</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize:15 }}>
            <thead>
              <tr style={{ background: "#FEF2F2" }}>
                {["Entity","Type","In Cycle","Risk Reason"].map(h=>(
                  <th key={h} style={{ padding:"10px 14px", textAlign:"left", fontWeight:700, fontSize:16, color:"#EF4444", letterSpacing:"0.5px", borderBottom:"2px solid #FECACA" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suspNodes.map((n,i)=>(
                <tr key={i} style={{ borderBottom:"1px solid #F1F5F9", background:i%2===0?"#FFFBFB":"#FFFFFF" }}>
                  <td style={{ padding:"9px 14px", fontWeight:600, color:"#1E293B" }}>{n.label||n.id}</td>
                  <td style={{ padding:"9px 14px", color:"#475569" }}>{n.type||"Entity"}</td>
                  <td style={{ padding:"9px 14px" }}>
                    <span style={{ padding:"2px 10px", borderRadius:10, fontSize:16, fontWeight:700, background:n.inCycle?"#FEE2E2":"#F0FDF4", color:n.inCycle?"#EF4444":"#059669" }}>
                      {n.inCycle?"YES":"No"}
                    </span>
                  </td>
                  <td style={{ padding:"9px 14px", color:"#EF4444", fontSize:16 }}>{n.reason||n.riskReason||"Anomalous pattern detected"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Circular chains */}
      {(gdata.cycle_summaries||[]).length > 0 && (
        <div className="glass" style={{ padding:"20px 20px", borderRadius:18, marginBottom:16 }}>
          <h3 style={{ fontSize:17, fontWeight:700, color:"#EF4444", letterSpacing:"1px", textTransform:"uppercase", marginBottom:14 }}>🔄 Circular Trading Chains Detected</h3>
          {gdata.cycle_summaries.slice(0,10).map((c,i)=>(
            <div key={i} style={{ padding:"10px 14px", borderRadius:10, marginBottom:8, background:"#FFF5F5", borderLeft:"4px solid #EF4444" }}>
              <span style={{ fontSize:17, color:"#334155", fontFamily:"monospace" }}>{c.description||(c.nodes||[]).join(" → ")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Clean bill */}
      {!suspNodes.length && !flags.length && cycleCount===0 && (
        <div className="glass" style={{ padding:"36px", borderRadius:20, textAlign:"center", border:"2px solid #10B981", background:"#F0FDF4" }}>
          <div style={{ fontSize:52, marginBottom:12 }}>✅</div>
          <div style={{ fontSize:21, fontWeight:800, color:"#059669", marginBottom:8 }}>Clean Fraud Assessment</div>
          <div style={{ fontSize:19, color:"#64748B" }}>No circular trading, no Benford anomalies, and no suspicious entities were detected during this analysis.</div>
        </div>
      )}
    </div>
  );
}
