import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

const TYPE_COLORS = {
  document:    "#36cceb",
  segment:     "#0ea5c9",
  feature:     "#0EA5E9",
  ml_model:    "#0EA5E9",
  hard_flag:   "#EF4444",
  policy_flag: "#F59E0B",
  decision:    "#10B981",
};

export default function EvidenceViewer({ analysis }) {
  const svgRef          = useRef(null);
  const gdata           = analysis?.evidence_graph || { nodes: [], links: [] };
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    if (!gdata.nodes?.length) return;
    const el = svgRef.current;
    const W = el.clientWidth || 900, H = 520;
    d3.select(el).selectAll("*").remove();

    const svg = d3.select(el).attr("width", W).attr("height", H).style("background", "#f8fffe");

    const sim = d3.forceSimulation(gdata.nodes)
      .force("link",    d3.forceLink(gdata.links).id(d => d.id).distance(90).strength(0.5))
      .force("charge",  d3.forceManyBody().strength(-130))
      .force("center",  d3.forceCenter(W / 2, H / 2))
      .force("collide", d3.forceCollide(18).strength(0.7));

    const link = svg.append("g").selectAll("line").data(gdata.links).enter().append("line")
      .attr("stroke", "#C7EEF5").attr("stroke-width", 1)
      .attr("stroke-dasharray", d => d.rel === "influences" ? "3 2" : "none");

    const node = svg.append("g").selectAll("circle").data(gdata.nodes).enter().append("circle")
      .attr("r", d => d.node_type === "decision" ? 18 : d.is_top_driver ? 12 : 8)
      .attr("fill", d => d.color || TYPE_COLORS[d.node_type] || "#9CA3AF")
      .attr("stroke", "#FFFFFF").attr("stroke-width", 2)
      .on("mouseover", (ev, d) => setTooltip({ x: ev.clientX, y: ev.clientY, d }))
      .on("mouseout",  () => setTooltip(null))
      .call(d3.drag()
        .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag",  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on("end",   (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

    svg.append("g").selectAll("text").data(gdata.nodes).enter().append("text")
      .text(d => (d.label || d.id).slice(0, 20))
      .attr("font-size", 8).attr("fill", "#94A3B8").attr("dy", 3).attr("dx", 14);

    sim.on("tick", () => {
      link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      node.attr("cx", d => d.x).attr("cy", d => d.y);
      svg.selectAll("text").attr("x", function(d) { return d?.x || 0; }).attr("y", function(d) { return d?.y || 0; });
    });
  }, [gdata]);

  const legendItems = Object.entries(TYPE_COLORS);

  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 14 }}>
        {legendItems.map(([type, color]) => (
          <span key={type} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10, color: "#64748B" }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: color, display: "inline-block" }} />
            {type}
          </span>
        ))}
      </div>

      <div className="glass" style={{ borderRadius: 16, overflow: "hidden", position: "relative" }}>
        {gdata.nodes?.length ? (
          <svg ref={svgRef} style={{ width: "100%", height: 520 }} />
        ) : (
          <div style={{ padding: 40, textAlign: "center" }}>
            <p style={{ fontSize: 40, marginBottom: 12 }}>🔍</p>
            <p style={{ color: "#64748B", fontSize: 13 }}>No evidence graph data returned.</p>
          </div>
        )}
        {tooltip && (
          <div
            style={{
              position: "fixed", zIndex: 50, top: tooltip.y + 10, left: tooltip.x + 10,
              background: "white", border: "1px solid #d0f5fb", borderRadius: 12, padding: "10px 14px",
              fontSize: 11, color: "#334155", maxWidth: 220, pointerEvents: "none",
              boxShadow: "0 4px 20px rgba(54,204,235,.2)",
            }}>
            <p style={{ fontWeight: 700, color: "#0891b2", marginBottom: 2 }}>{tooltip.d.label}</p>
            <p style={{ color: "#64748B" }}>Type: {tooltip.d.node_type}</p>
            {tooltip.d.value !== undefined && <p>Value: {tooltip.d.value}</p>}
            {tooltip.d.is_top_driver && <p style={{ color: "#F59E0B" }}>⭐ Top SHAP Driver</p>}
          </div>
        )}
      </div>

      <div className="glass" style={{ marginTop: 12, padding: "14px 20px", borderRadius: 12, display: "flex", gap: 32 }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 9, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 4, fontWeight: 600 }}>Nodes</p>
          <p style={{ fontSize: 18, fontWeight: 800, color: "#36cceb" }}>{gdata.stats?.total_nodes || 0}</p>
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 9, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 4, fontWeight: 600 }}>Edges</p>
          <p style={{ fontSize: 18, fontWeight: 800, color: "#0ea5c9" }}>{gdata.stats?.total_edges || 0}</p>
        </div>
      </div>
    </div>
  );
}
