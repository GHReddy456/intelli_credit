import React, { useMemo } from "react";

const TYPE_META = {
  document:    { icon:"📄", label:"Document Processed",    color:"#0891b2", bg:"rgba(8,145,178,0.1)"   },
  segment:     { icon:"📑", label:"Document Section",      color:"#7C3AED", bg:"rgba(124,58,237,0.1)"  },
  feature:     { icon:"📊", label:"Financial Feature",     color:"#059669", bg:"rgba(5,150,105,0.1)"   },
  ml_model:    { icon:"🤖", label:"ML Model Signal",       color:"#D97706", bg:"rgba(217,119,6,0.1)"   },
  hard_flag:   { icon:"🚫", label:"Hard Reject Trigger",   color:"#DC2626", bg:"rgba(220,38,38,0.1)"   },
  policy_flag: { icon:"⚠️",  label:"Policy Flag",           color:"#D97706", bg:"rgba(217,119,6,0.08)"  },
  decision:    { icon:"⚖️",  label:"Final Decision Signal", color:"#10b981", bg:"rgba(16,185,129,0.1)"  },
};

function humanizeLabel(str) {
  return (str || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function SectionGroup({ type, nodes, isDark = true }) {
  const meta = TYPE_META[type] || { icon:"🔹", label:humanizeLabel(type), color:"#64748B", bg: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)" };
  return (
    <div style={{marginBottom:24}}>
      <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}>
        <span style={{fontSize:21}}>{meta.icon}</span>
        <h4 style={{fontSize:15,fontWeight:700,color:meta.color,letterSpacing:"0.5px",margin:0,textTransform:"uppercase"}}>
          {meta.label}s
          <span style={{fontWeight:400,color:isDark ? "rgba(255,255,255,0.38)" : "#94A3B8",fontSize:17,marginLeft:6}}>({nodes.length})</span>
        </h4>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(240px,1fr))",gap:10}}>
        {nodes.map((node, i) => (
          <div key={i} style={{
            padding:"14px 16px",borderRadius:12,
            background:meta.bg,
            border:`1.5px solid ${meta.color}30`,
            position:"relative",
          }}>
            {node.is_top_driver && (
              <div style={{
                position:"absolute",top:8,right:8,
                fontSize:15,fontWeight:700,color:"#f59e0b",
                background:"rgba(245,158,11,0.15)",padding:"2px 7px",borderRadius:20,
                border:"1px solid rgba(245,158,11,0.5)",
              }}>⭐ KEY DRIVER</div>
            )}
            <div style={{fontSize:15,fontWeight:700,color:meta.color,marginBottom:5,lineHeight:1.3,paddingRight:node.is_top_driver?58:0}}>
              {humanizeLabel(node.label || node.id)}
            </div>
            {node.value !== undefined && node.value !== null && (
              <div style={{fontSize:17,color:isDark ? "#cbd5e1" : "#334155",marginBottom:3}}>
                Value: <strong>{typeof node.value === "number" ? (node.value === 0 && node.node_type === "feature" ? "0.00" : node.value.toFixed(2)) : String(node.value)}</strong>
              </div>
            )}
            {node.description && (
              <div style={{fontSize:16,color:isDark ? "rgba(255,255,255,0.45)" : "#64748B",lineHeight:1.5,marginTop:4}}>{node.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EvidenceViewer({ analysis, theme = "dark" }) {
  const isDark = theme !== "light";
  const gdata = analysis?.evidence_graph || { nodes: [], links: [] };
  const nodes = gdata.nodes || [];

  const grouped = useMemo(() => {
    const ORDER = ["document","segment","feature","ml_model","hard_flag","policy_flag","decision"];
    const map = {};
    nodes.forEach(n => {
      const t = n.node_type || "unknown";
      if (!map[t]) map[t] = [];
      map[t].push(n);
    });
    const sorted = [];
    ORDER.forEach(t => { if (map[t]?.length) sorted.push([t, map[t]]); });
    Object.entries(map).forEach(([t, ns]) => { if (!ORDER.includes(t)) sorted.push([t, ns]); });
    return sorted;
  }, [nodes]);

  const topDrivers = nodes.filter(n => n.is_top_driver);
  const hardFlags  = nodes.filter(n => n.node_type === "hard_flag");

  if (!nodes.length) {
    return (
      <div className="glass" style={{padding:60,textAlign:"center",borderRadius:16}}>
        <p style={{fontSize:43,marginBottom:12}}>🔍</p>
        <p style={{color:isDark ? "rgba(255,255,255,0.45)" : "#64748B",fontSize:17}}>No evidence data available for this application.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Summary row */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:14,marginBottom:24}}>
        {[
          {label:"Total Evidence Points",value:nodes.length,           color:"#0891b2",bg:"rgba(8,145,178,0.1)"},
          {label:"Key Decision Drivers", value:topDrivers.length,      color:"#D97706",bg:"rgba(217,119,6,0.1)"},
          {label:"Hard Reject Flags",    value:hardFlags.length,       color:"#DC2626",bg:"rgba(220,38,38,0.1)"},
          {label:"Evidence Links",       value:gdata.stats?.total_edges||gdata.links?.length||0,color:"#059669",bg:"rgba(5,150,105,0.1)"},
        ].map(s => (
          <div key={s.label} className="glass" style={{
            padding:"18px",borderRadius:14,
            background:s.bg,border:`1.5px solid ${s.color}25`,
            textAlign:"center",
          }}>
            <div style={{fontSize:31,fontWeight:900,color:s.color,marginBottom:4,lineHeight:1}}>{s.value}</div>
            <div style={{fontSize:16,color:isDark ? "rgba(255,255,255,0.5)" : "#64748B",fontWeight:600,lineHeight:1.3}}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Explainer */}
      <div className="glass" style={{
        padding:"16px 20px",borderRadius:12,marginBottom:24,
        background:"rgba(16,185,129,0.06)",border:"1.5px solid rgba(16,185,129,.2)",
      }}>
        <p style={{fontSize:15,color:"#10b981",fontWeight:700,marginBottom:5}}>📖 How to read this view</p>
        <p style={{fontSize:17,color:isDark ? "#cbd5e1" : "#334155",lineHeight:1.75,margin:0}}>
          Each card below represents a <strong>signal</strong> that contributed to the credit decision — from raw documents
          ingested, to financial features extracted, to ML model outputs and policy flags.
          Cards marked <strong style={{color:"#D97706"}}>⭐ KEY DRIVER</strong> had the highest statistical
          influence (SHAP value) on the ML credit score. Sections are ordered by evidence type,
          from data source through to final verdict.
        </p>
      </div>

      {/* Grouped evidence cards */}
      {grouped.map(([type, typeNodes]) => (
        <SectionGroup key={type} type={type} nodes={typeNodes} isDark={isDark} />
      ))}
    </div>
  );
}
