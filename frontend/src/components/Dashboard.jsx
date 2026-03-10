import React, { useState, useEffect } from "react";

const FIVE_CS = ["character","capacity","capital","collateral","conditions"];

const FIVE_CS_META = {
  character:   { icon:"🧑‍💼", desc:"Promoter integrity, litigation history, governance quality", color:"#ec5b13",  bg:"rgba(236,91,19,0.15)" },
  capacity:    { icon:"📈", desc:"Ability to repay — DSCR, revenue stability, cash flow strength", color:"#36cceb",  bg:"rgba(54,204,235,0.12)" },
  capital:     { icon:"💰", desc:"Net worth, equity buffer, leverage and debt structure", color:"#10b981",  bg:"rgba(16,185,129,0.12)" },
  collateral:  { icon:"🏦", desc:"Security coverage, quality of assets pledged against the loan", color:"#f59e0b",  bg:"rgba(245,158,11,0.12)" },
  conditions:  { icon:"🏭", desc:"Sector tailwinds / headwinds, macroeconomic environment rating", color:"#ef4444",  bg:"rgba(239,68,68,0.12)"  },
};

/* ── Inline SVG Sparkline ──────────────────────────────── */
function Sparkline({ series = [], color = "#059669", height = 30, width = 80 }) {
  if (!series || series.length < 2) return null;
  const vals = series.map(Number).filter(isFinite);
  if (vals.length < 2) return null;
  const min = Math.min(...vals), max = Math.max(...vals);
  const range = max - min || 1;
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const trend = vals[vals.length - 1] - vals[0];
  const col = trend >= 0 ? color : "#DC2626";
  return (
    <svg width={width} height={height} style={{overflow:"visible"}}>
      <polyline points={pts} fill="none" stroke={col} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round"
        style={{filter:`drop-shadow(0 0 3px ${col}60)`}} />
      <circle cx={pts.split(" ").at(-1).split(",")[0]} cy={pts.split(" ").at(-1).split(",")[1]}
        r="3" fill={col} />
    </svg>
  );
}

/* ── Animated SVG Score Gauge ────────────────────────── */
function AnimGauge({ score, isDark = true }) {
  const [ready, setReady] = useState(false);
  useEffect(() => { const t = setTimeout(() => setReady(true), 200); return () => clearTimeout(t); }, []);
  const pct = Math.min(100, Math.max(0, score || 0));
  const R   = 70;
  const circ = 2 * Math.PI * R;
  const offset = circ - (pct / 100) * circ;
  const col  = pct >= 75 ? "#10B981" : pct >= 60 ? "#F59E0B" : "#EF4444";

  return (
    <svg width="180" height="180" viewBox="0 0 180 180" style={{borderRadius:"50%"}}>
      {/* Track ring */}
      <circle cx="90" cy="90" r={R} fill="none" stroke={isDark ? "rgba(34,22,16,0.9)" : "rgba(0,0,0,0.1)"} strokeWidth="14" />
      {/* Glow halo */}
      <circle cx="90" cy="90" r={R} fill="none" stroke={col} strokeWidth="18" opacity=".12"
        strokeDasharray={circ}
        strokeDashoffset={ready ? offset : circ}
        strokeLinecap="round" transform="rotate(-90 90 90)"
        style={{transition:"stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)",filter:`blur(6px)`}}
      />
      {/* Main stroke */}
      <circle cx="90" cy="90" r={R} fill="none" stroke={col} strokeWidth="11"
        strokeDasharray={circ}
        strokeDashoffset={ready ? offset : circ}
        strokeLinecap="round" transform="rotate(-90 90 90)"
        style={{
          transition: "stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1)",
          filter: `drop-shadow(0 0 6px ${col})`,
        }}
      />
      {/* Score number */}
      <text x="90" y="83" textAnchor="middle" dominantBaseline="central"
        fontSize="34" fontWeight="900" fill={col}
        style={{animation: ready ? "number-pop .5s ease both" : "none"}}>
        {pct.toFixed(0)}
      </text>
      <text x="90" y="110" textAnchor="middle" fontSize="10" fill={isDark ? "rgba(255,255,255,0.4)" : "rgba(0,0,0,0.45)"} fontWeight="600">
        CREDIT SCORE
      </text>
    </svg>
  );
}

/* ── Metric Card ─────────────────────────────── */
function MetricCard({ label, value, sub, tone, delay = 0, series, benchmarkLabel, compLabel, isDark = true }) {
  const palettes = {
    green:   { accent:"#10b981", subColor:"#10b981" },
    amber:   { accent:"#f59e0b", subColor:"#f59e0b" },
    red:     { accent:"#ef4444", subColor:"#ef4444" },
    neutral: { accent: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)", subColor: isDark ? "rgba(255,255,255,0.38)" : "#64748B" },
    blue:    { accent:"#ec5b13", subColor:"#ec5b13" },
  };
  const p = palettes[tone] || palettes.blue;
  return (
    <div className="glass-hover" style={{
      padding:"16px 16px 14px 18px",
      borderRadius:12,
      background: isDark ? "rgba(26,14,7,0.92)" : "rgba(255,255,255,0.95)",
      border: isDark ? "1px solid rgba(255,255,255,0.055)" : "1px solid rgba(0,0,0,0.08)",
      borderLeft:`3px solid ${p.accent}`,
      animation:`fadeInUp .55s ease ${delay}s both`,
      display:"flex",flexDirection:"column",gap:0,
    }}>
      <p style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.36)" : "#64748B",marginBottom:8,textTransform:"uppercase",letterSpacing:"0.8px",fontWeight:700,lineHeight:1}}>
        {label}{benchmarkLabel ? ` (VS ${benchmarkLabel})` : ""}
      </p>
      <p style={{fontSize:29,fontWeight:800,color: isDark ? "#f1f5f9" : "#1E293B",lineHeight:1,marginBottom:compLabel||sub?8:0}}>{value}</p>
      {compLabel && (
        <p style={{fontSize:15,fontWeight:700,color:p.subColor,margin:0,letterSpacing:"0.2px"}}>{compLabel}</p>
      )}
      {sub && !compLabel && <p style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.35)" : "#94A3B8",margin:0}}>{sub}</p>}
      {series?.length >= 2 && (
        <div style={{marginTop:8}}>
          <Sparkline series={series} color={p.accent} />
        </div>
      )}
    </div>
  );
}

/* ── SVG Risk Radar (spider chart) ─────────────────────────── */
function RiskRadar({ data }) {
  const axes = data?.axes || [];
  if (axes.length < 3) return null;
  const n = axes.length;
  const cx = 140, cy = 140, r = 110;
  const pts = (vals, scale) => vals.map((v, i) => {
    const ang = (Math.PI * 2 * i) / n - Math.PI / 2;
    const rr  = (v / 100) * r * scale;
    return [cx + rr * Math.cos(ang), cy + rr * Math.sin(ang)];
  });
  const toSVG = arr => arr.map(p => p.join(",")).join(" ");
  const ringPts  = idx => pts(Array(n).fill(idx * 25), 1);
  const dataPts  = pts(axes.map(a => a.score || 0), 1);
  const labelPts = pts(Array(n).fill(1), 1.28);
  const riskColor = s => s >= 70 ? "#DC2626" : s >= 40 ? "#D97706" : "#059669";

  return (
    <svg width="280" height="280" viewBox="0 0 280 280">
      {/* Ring guides */}
      {[1,2,3,4].map(i => (
        <polygon key={i} points={toSVG(ringPts(i))}
          fill="none" stroke="rgba(236,91,19,0.12)" strokeWidth="0.8" />
      ))}
      {/* Spokes */}
      {axes.map((_, i) => {
        const [x, y] = pts([1], 1)[0] || [cx, cy];
        const ang = (Math.PI * 2 * i) / n - Math.PI / 2;
        return <line key={i} x1={cx} y1={cy}
          x2={cx + r * Math.cos(ang)} y2={cy + r * Math.sin(ang)}
          stroke="rgba(236,91,19,0.12)" strokeWidth="0.8" />;
      })}
      {/* Data polygon fill */}
      <polygon points={toSVG(dataPts)}
        fill="rgba(236,91,19,0.25)" stroke="#ec5b13" strokeWidth="2"
        strokeLinejoin="round" style={{filter:"drop-shadow(0 0 4px rgba(236,91,19,0.3))"}} />
      {/* Data dots */}
      {dataPts.map(([x,y], i) => (
        <circle key={i} cx={x} cy={y} r="4.5" fill={riskColor(axes[i].score||0)}
          style={{filter:`drop-shadow(0 0 3px ${riskColor(axes[i].score||0)})`}} />
      ))}
      {/* Labels */}
      {axes.map((a, i) => {
        const [x, y] = labelPts[i];
        const anchor = x < cx - 2 ? "end" : x > cx + 2 ? "start" : "middle";
        return (
          <text key={i} x={x} y={y} textAnchor={anchor}
            dominantBaseline="central" fontSize="8.5" fontWeight="700"
            fill={riskColor(a.score||0)}>
            {a.name} ({a.score?.toFixed(0)||"N/A"})
          </text>
        );
      })}
    </svg>
  );
}

export default function Dashboard({ analysis, theme = "dark" }) {
  const isDark = theme !== "light";
  const dec   = analysis?.decision  || {};
  const feat  = analysis?.features  || {};
  const fraud = analysis?.fraud     || {};
  const fiveCs = dec.five_cs_scores || {};
  const disp  = feat._display_ratios || {};

  const score  = dec.credit_score || 0;
  const tone   = score >= 75 ? "green" : score >= 60 ? "amber" : "red";
  const gCls   = score >= 75 ? "glow-green" : score >= 60 ? "glow-amber" : "glow-red";
  const vLabel = (dec.verdict||"").replace(/_/g," ");
  const vColor = dec.verdict==="APPROVE" ? "#10B981" : dec.verdict==="CONDITIONAL_APPROVE" ? "#F59E0B" : "#EF4444";

  /* derived metric tones */
  const dscrTone  = (feat.dscr||0) >= 1.5  ? "green" : (feat.dscr||0) >= 1 ? "amber" : "red";
  const deTone    = (feat.debt_to_equity||0) <= 1.5 ? "green" : (feat.debt_to_equity||0) <= 3 ? "amber" : "red";
  const crTone    = (feat.current_ratio||0) >= 1.5  ? "green" : (feat.current_ratio||0) >= 1 ? "amber" : "red";
  const ebtTone   = (feat.ebitda_margin||0) >= 0.15 ? "green" : (feat.ebitda_margin||0) >= 0.08 ? "amber" : "red";
  const fraudTone = (fraud.fraud_risk_score||0) <= 25 ? "green" : (fraud.fraud_risk_score||0) <= 55 ? "amber" : "red";
  const pdTone    = (dec.probability_of_default||0) <= 0.15 ? "green" : (dec.probability_of_default||0) <= 0.35 ? "amber" : "red";

  /* sector benchmarks */
  const benchmarks = feat._sector_benchmarks || {};
  const medians    = benchmarks.medians || {};
  const sectorName = (benchmarks.sector || "").replace(/_/g," ");

  /* governance */
  const govScore = feat._character_score ?? null;

  /* NLP-friendly verdict reason */
  const nlpReason = (() => {
    const raw = dec.reason || "";
    if (!raw) return "";
    return raw
      .replace(/Hard reject:\s*/gi, "")
      .replace(/Litigation severity score exceeds threshold \(([0-9.]+)\s*>\s*([0-9.]+)\)/i,
        (_, a, l) => `Promoter/company litigation severity is critically high (score ${parseFloat(a).toFixed(2)}, acceptable limit: ${parseFloat(l).toFixed(2)}). Active legal proceedings pose material credit risk and trigger a hard reject.`)
      .replace(/([a-z_]+)\s+score\s+exceeds\s+threshold\s+\(([0-9.]+)\s*>\s*([0-9.]+)\)/gi,
        (_, m, a, l) => `${m.replace(/_/g," ")} is above the acceptable ceiling (${parseFloat(a).toFixed(2)} vs limit ${parseFloat(l).toFixed(2)}).`)
      .replace(/([a-z_]+)\s+below\s+minimum\s+\(([0-9.]+)\s*<\s*([0-9.]+)\)/gi,
        (_, m, a, l) => `${m.replace(/_/g," ")} is below the minimum requirement (${parseFloat(a).toFixed(2)} vs required ${parseFloat(l).toFixed(2)}).`);
  })();

  const riskTitle = dec.verdict === "APPROVE"
    ? "Credit Application: Approved for Sanction"
    : dec.verdict === "CONDITIONAL_APPROVE"
    ? "Credit Application: Conditional Approval"
    : "High Risk Alert: Hard Reject Triggered";

  const cmpLabel = (t, type) => {
    if (type === "pd")
      return t === "green" ? "↓ Low Risk"    : t === "amber" ? "→ Elevated Risk" : "↑ High Risk";
    if (type === "fraud")
      return t === "green" ? "✓ Clean Sheet" : t === "amber" ? "→ Monitor"        : "⚠ High Fraud Risk";
    if (type === "lit")
      return t === "green" ? "✓ No Cases"    : "⚠ Active Cases";
    if (type === "ebitda")
      return t === "green" ? "↑ Above Peers" : t === "amber" ? "→ Near Peers"     : "↘ Below Peers";
    if (type === "cr")
      return t === "green" ? "↑ Above Target": t === "amber" ? "→ Adequate"       : "△ Critical Low";
    return t === "green" ? "↑ Above Target" : t === "amber" ? "→ Near Target" : "↓ Below Target";
  };

  return (
    <div style={{display:"flex",flexDirection:"column",gap:14}}>

      {/* ── Row 1: 3-col header ───────────────────────── */}
      <div style={{display:"grid",gridTemplateColumns:"160px 1fr 190px",gap:14,alignItems:"stretch"}}
        className="fade-in-up">

        {/* GRADE BADGE */}
        <div className="glass" style={{
          padding:"22px 14px",borderRadius:18,
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:10,
        }}>
          <div style={{
            width:68,height:68,borderRadius:14,
            background:`${vColor}15`,border:`2px solid ${vColor}50`,
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:39,fontWeight:900,color:vColor,
            boxShadow:`0 0 22px ${vColor}30`,
          }}>
            {dec.risk_grade?.[0] || "—"}
          </div>
          <div style={{fontSize:14,fontWeight:700,color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8",textTransform:"uppercase",letterSpacing:"1.2px",textAlign:"center"}}>RISK GRADE</div>
          <div style={{
            padding:"3px 14px",borderRadius:20,fontSize:16,fontWeight:800,letterSpacing:"0.5px",
            background:`${vColor}20`,border:`1px solid ${vColor}50`,color:vColor,
            display:"flex",alignItems:"center",gap:4,
          }}>
            {dec.verdict === "REJECT" ? "⊘" : dec.verdict === "APPROVE" ? "✓" : "⚡"} {vLabel || "—"}
          </div>
        </div>

        {/* TITLE + DESCRIPTION */}
        <div className="glass" style={{padding:"22px 26px",borderRadius:18,border: isDark ? "1px solid rgba(255,255,255,0.07)" : "1px solid rgba(0,0,0,0.07)"}}>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
            <span style={{
              padding:"2px 10px",borderRadius:5,fontSize:15,fontWeight:800,letterSpacing:"0.4px",
              background:"rgba(236,91,19,0.1)",border:"1px solid rgba(236,91,19,0.5)",color:"#ec5b13",
            }}>Case ID: {(analysis?.job_id||"IC-000000").slice(0,8).toUpperCase()}</span>
            <span style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.32)" : "#94A3B8",fontWeight:400}}>
              Report generated on {new Date().toLocaleDateString("en-US",{month:"short",day:"2-digit",year:"numeric"})}
            </span>
          </div>
          <h2 style={{margin:"0 0 10px",fontSize:21,fontWeight:800,color: isDark ? "#f1f5f9" : "#1E293B",lineHeight:1.25}}>
            {riskTitle}
          </h2>
          <p style={{margin:0,fontSize:17,color: isDark ? "#cbd5e1" : "#334155",lineHeight:1.65,maxHeight:85,overflow:"hidden"}}>
            {nlpReason || dec.reason || "Analysis complete. Review the metrics below for a full assessment."}
          </p>
          {dec.loan_details?.max_loan_crore && (
            <div style={{display:"flex",gap:22,flexWrap:"wrap",marginTop:14}}>
              {[
                {l:"Loan Limit",   v:`₹${dec.loan_details.max_loan_crore} Cr`,    c:"#10b981"},
                {l:"Interest",     v:`${dec.loan_details.interest_rate_pct}%`,     c:"#36cceb"},
                {l:"Tenure",       v:`${dec.loan_details.tenure_years} yr`,        c:"#10b981"},
                {l:"Risk Premium", v:`+${dec.loan_details.risk_premium_pct}%`,     c:"#f59e0b"},
              ].map(item => (
                <div key={item.l}>
                  <div style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.38)" : "#94A3B8",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:2}}>{item.l}</div>
                  <div style={{fontSize:19,fontWeight:800,color:item.c}} className="num-pop">{item.v}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* GAUGE */}
        <div className={`glass ${gCls}`} style={{
          padding:"16px",borderRadius:18,
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:6,
        }}>
          <AnimGauge score={score} isDark={isDark} />
          <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",letterSpacing:"0.8px",fontWeight:600,marginTop:2}}>
            {dec.risk_grade || "—"}
          </div>
        </div>
      </div>

      {/* ── Row 2: 8 Metric cards ─────────────────────── */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12}}>
        <MetricCard label="DSCR" value={disp.dscr != null ? `${disp.dscr.toFixed(2)}×` : "N/A"}
          tone={disp.dscr != null ? dscrTone : "neutral"} delay={0} isDark={isDark}
          benchmarkLabel={medians.dscr ? `${medians.dscr}×` : undefined}
          compLabel={disp.dscr != null ? cmpLabel(dscrTone,"ratio") : "Data not available"}
          series={feat._cfo_series?.length >= 2 ? feat._cfo_series : undefined} />
        <MetricCard label="DEBT/EQUITY" value={disp.debt_to_equity != null ? `${disp.debt_to_equity.toFixed(2)}×` : "N/A"}
          tone={disp.debt_to_equity != null ? deTone : "neutral"} delay={0.05} isDark={isDark}
          benchmarkLabel={medians.debt_to_equity ? `${medians.debt_to_equity}×` : undefined}
          compLabel={disp.debt_to_equity != null ? cmpLabel(deTone,"ratio") : "Data not available"} />
        <MetricCard label="CURRENT RATIO" value={disp.current_ratio != null ? `${disp.current_ratio.toFixed(2)}×` : "N/A"}
          tone={disp.current_ratio != null ? crTone : "neutral"} delay={0.1} isDark={isDark}
          benchmarkLabel={medians.current_ratio ? `${medians.current_ratio}×` : undefined}
          compLabel={disp.current_ratio != null ? cmpLabel(crTone,"cr") : "Data not available"} />
        <MetricCard label="EBITDA MARGIN" value={disp.ebitda_margin != null ? `${(disp.ebitda_margin*100).toFixed(1)}%` : "N/A"}
          tone={disp.ebitda_margin != null ? ebtTone : "neutral"} delay={0.15} isDark={isDark}
          benchmarkLabel={medians.ebitda_margin ? `${(medians.ebitda_margin*100).toFixed(0)}%` : undefined}
          compLabel={disp.ebitda_margin != null ? cmpLabel(ebtTone,"ebitda") : "Data not available"}
          series={feat._ebitda_series?.length >= 2 ? feat._ebitda_series : undefined} />
        <MetricCard label="REVENUE CAGR" value={disp.revenue_growth_3yr != null ? `${(disp.revenue_growth_3yr*100).toFixed(1)}%` : "N/A"}
          tone={disp.revenue_growth_3yr != null ? ((feat.revenue_growth_3yr||0)>=0.08?"green":(feat.revenue_growth_3yr||0)>=0?"amber":"red") : "neutral"}
          delay={0.2} isDark={isDark}
          compLabel={disp.revenue_growth_3yr != null ? cmpLabel((feat.revenue_growth_3yr||0)>=0.08?"green":(feat.revenue_growth_3yr||0)>=0?"amber":"red","ratio") : "Data not available"}
          series={feat._revenue_series?.length >= 2 ? feat._revenue_series : undefined} />
        <MetricCard label="FRAUD RISK" value={`${(fraud.fraud_risk_score||0).toFixed(0)}/100`}
          tone={fraudTone} delay={0.25} isDark={isDark}
          compLabel={(fraud.all_flags||[]).length > 0 ? (fraudTone === "green" ? "→ Minor Flags" : fraudTone === "amber" ? "⚠ Flags Detected" : "⚠ High Fraud Risk") : cmpLabel(fraudTone,"fraud")} />
        <MetricCard label="LITIGATION CASES" value={feat.litigation_count || 0}
          tone={(feat.litigation_count||0)===0?"green":"red"} delay={0.3} isDark={isDark}
          compLabel={cmpLabel((feat.litigation_count||0)===0?"green":"red","lit")} />
        <MetricCard label="PROB. OF DEFAULT" value={`${((dec.probability_of_default||0)*100).toFixed(1)}%`}
          tone={pdTone} delay={0.35} isDark={isDark}
          compLabel={cmpLabel(pdTone,"pd")} />
      </div>

      {/* ── Row 3: Governance (left) + Risk Radar (right) ── */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 300px",gap:14,alignItems:"stretch"}}>

        {/* GOVERNANCE */}
        {govScore !== null ? (
          <div className="glass" style={{padding:"20px 22px",borderRadius:16}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>
              <h3 style={{fontSize:15,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:0}}>
                🧑‍💼 Governance &amp; Character Risk Score
              </h3>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:27,fontWeight:900,color:govScore>=70?"#10b981":govScore>=50?"#f59e0b":"#ef4444",lineHeight:1}}>
                  {govScore.toFixed(0)}<span style={{fontSize:17,fontWeight:400,color: isDark ? "rgba(255,255,255,0.35)" : "#94A3B8"}}>/100</span>
                </div>
                <div style={{fontSize:14,fontWeight:700,marginTop:2,textTransform:"uppercase",letterSpacing:"0.5px",
                  color:govScore>=70?"#10b981":govScore>=50?"#f59e0b":"#ef4444"}}>
                  {govScore>=70?"LOW RISK":govScore>=50?"MODERATE RISK":"HIGH RISK"}
                </div>
              </div>
            </div>
            <div style={{height:8,borderRadius:4,background:"rgba(236,91,19,0.1)",overflow:"hidden",marginBottom:16}}>
              <div style={{
                height:"100%",borderRadius:4,width:`${govScore}%`,
                background:`linear-gradient(90deg,${govScore>=70?"#10b981":"#ef4444"},${govScore>=70?"#34d399":"#fca5a5"})`,
                transition:"width 1.2s cubic-bezier(.4,0,.2,1)",
              }} />
            </div>
            {/* Sub-factor grid cards */}
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
              {[
                {label:"Litigation Severity",  val:`${((feat.litigation_severity_score||0)*100).toFixed(0)}%`, ok:(feat.litigation_severity_score||0)<0.3},
                {label:"GST Mismatch",          val:`${((feat.gst_bank_mismatch_score||0)*100).toFixed(0)}%`,  ok:(feat.gst_bank_mismatch_score||0)<0.15},
                {label:"Benford Deviation",     val:`${((feat.benford_deviation_score||0)*100).toFixed(0)}%`,  ok:(feat.benford_deviation_score||0)<0.3},
                {label:"Circular Trading",      val:`${((feat.circular_trading_score||0)*100).toFixed(0)}%`,   ok:(feat.circular_trading_score||0)<0.3},
                {label:"Regulatory Violations", val:feat.regulatory_violation_count?.toFixed(0)||"0",           ok:(feat.regulatory_violation_count||0)<=1},
              ].map(f=>(
                <div key={f.label} style={{
                  padding:"10px 14px",borderRadius:10,
                  background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)",
                  border:`1px solid ${f.ok?"rgba(16,185,129,0.2)":"rgba(239,68,68,0.25)"}`,
                }}>
                  <div style={{fontSize:14,fontWeight:600,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:4}}>
                    {f.label}
                  </div>
                  <div style={{fontSize:23,fontWeight:800,color:f.ok?"#10b981":"#ef4444"}}>{f.val}</div>
                </div>
              ))}
            </div>
          </div>
        ) : <div />}

        {/* RISK RADAR */}
        {analysis?.risk_radar?.axes?.length >= 3 && (
          <div className="glass" style={{padding:"18px 16px",borderRadius:16,display:"flex",flexDirection:"column",alignItems:"center"}}>
            <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 2px",alignSelf:"flex-start"}}>
              🎯 Risk Radar
            </h3>
            <p style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",marginBottom:6,marginTop:2,alignSelf:"flex-start"}}>
              Higher = more risk. Target: all &lt;50.
            </p>
            <RiskRadar data={analysis.risk_radar} />
            <div style={{display:"flex",gap:14,marginTop:6,justifyContent:"center",flexWrap:"wrap"}}>
              {[
                {l:"Score", v:`${analysis.risk_radar.credit_score?.toFixed(0)||"N/A"}`, c:"#10b981"},
                {l:"Grade", v:analysis.risk_radar.risk_grade||"N/A",                    c:"#36cceb"},
                {l:"PD",    v:analysis.risk_radar.pd_pct!=null?`${analysis.risk_radar.pd_pct.toFixed(1)}%`:"N/A", c:"#ef4444"},
              ].map(({l,v,c})=>(
                <div key={l} style={{textAlign:"center"}}>
                  <div style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",fontWeight:600}}>{l}</div>
                  <div style={{fontSize:15,fontWeight:900,color:c}}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Row 4: GST Table (left) + Five Cs compact (right) ── */}
      {(() => {
        const gstBank = analysis?.verification?.gst_bank || {};
        const recon   = gstBank.monthly_reconciliation || [];
        const hasFiveCs = FIVE_CS.some(c => fiveCs[c] || (c==="character" && feat._character_score));
        if (recon.length === 0 && !hasFiveCs) return null;
        const statusColor = s => s==="OK"||s==="MATCHED"?"#10b981":s==="HIGH"||s==="DEVIATION"?"#ef4444":s==="MEDIUM"?"#f59e0b":"rgba(255,255,255,0.3)";
        return (
          <div style={{display:"grid",gridTemplateColumns:"1fr 280px",gap:14,alignItems:"start"}}>

            {/* GST TABLE */}
            {recon.length > 0 && (
              <div className="glass" style={{padding:"18px 20px",borderRadius:16}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}>
                  <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:0}}>
                    📊 GST vs Bank Statement Reconciliation
                  </h3>
                  {gstBank.gst_turnover && (
                    <div style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",padding:"3px 9px",borderRadius:8,background:"rgba(236,91,19,0.1)",border:"1px solid rgba(236,91,19,0.2)"}}>
                      Annual GST: ₹{gstBank.gst_turnover.toLocaleString("en-IN")}
                    </div>
                  )}
                </div>
                <div style={{overflowX:"auto"}}>
                  <table style={{width:"100%",borderCollapse:"collapse",fontSize:16}}>
                    <thead>
                      <tr style={{borderBottom:"1px solid rgba(236,91,19,0.25)"}}>
                        {["Month","GSTR-1 Turnover","Bank Credits","Delta %","Status"].map(h=>(
                          <th key={h} style={{
                            padding:"6px 10px",fontWeight:700,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B",
                            textTransform:"uppercase",fontSize:14,letterSpacing:"0.5px",
                            textAlign:h==="Month"||h==="Status"?"left":"right",
                          }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {recon.map((row,i)=>(
                        <tr key={row.month} style={{
                          borderBottom: isDark ? "1px solid rgba(255,255,255,0.04)" : "1px solid rgba(0,0,0,0.05)",
                          background: isDark ? (i%2===0?"rgba(255,255,255,0.02)":"transparent") : (i%2===0?"rgba(0,0,0,0.02)":"transparent"),
                        }}>
                          <td style={{padding:"7px 10px",fontWeight:600,color: isDark ? "#f1f5f9" : "#1E293B",fontSize:16}}>{row.month}</td>
                          <td style={{padding:"7px 10px",textAlign:"right",color: isDark ? "#cbd5e1" : "#334155",fontSize:16}}>
                            {row.gst_turnover!=null?`₹${Number(row.gst_turnover).toLocaleString("en-IN")}`:"NO_DATA"}
                          </td>
                          <td style={{padding:"7px 10px",textAlign:"right",color: isDark ? "#cbd5e1" : "#334155",fontSize:16}}>
                            {row.bank_credits!=null?`₹${Number(row.bank_credits).toLocaleString("en-IN")}`:"NO_DATA"}
                          </td>
                          <td style={{padding:"7px 10px",textAlign:"right",fontWeight:700,color:statusColor(row.status),fontSize:16}}>
                            {row.delta_pct!=null?`${row.delta_pct>0?"+":""}${row.delta_pct}%`:"—"}
                          </td>
                          <td style={{padding:"7px 10px"}}>
                            <span style={{
                              padding:"2px 8px",borderRadius:10,fontSize:14,fontWeight:700,
                              background:`${statusColor(row.status)}18`,
                              color:statusColor(row.status),
                              border:`1px solid ${statusColor(row.status)}30`,
                            }}>{row.status}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* FIVE Cs COMPACT LIST */}
            {hasFiveCs && (
              <div className="glass" style={{padding:"18px 18px",borderRadius:16}}>
                <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 18px"}}>
                  Five Cs Assessment
                </h3>
                <div style={{display:"flex",flexDirection:"column",gap:13}}>
                  {FIVE_CS.map(c => {
                    const sc = (c==="character"&&(!fiveCs[c]||fiveCs[c]===0)&&feat._character_score)
                      ? feat._character_score : (fiveCs[c]||0);
                    const meta = FIVE_CS_META[c];
                    const col = sc>=70?"#10b981":sc>=50?"#f59e0b":"#ef4444";
                    return (
                      <div key={c}>
                        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:5}}>
                          <div style={{fontSize:16,fontWeight:600,color: isDark ? "rgba(255,255,255,0.65)" : "#334155",textTransform:"capitalize"}}>
                            {meta.icon} {c}
                          </div>
                          <div style={{fontSize:17,fontWeight:800,color:col}}>{sc.toFixed(0)}/100</div>
                        </div>
                        <div style={{height:6,borderRadius:3,background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.08)",overflow:"hidden"}}>
                          <div style={{
                            height:"100%",borderRadius:3,width:`${sc}%`,
                            background:`linear-gradient(90deg,${col}80,${col})`,
                            transition:"width 1s cubic-bezier(.4,0,.2,1)",
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Row 5: SHAP (left) + Facility + Sector + Borrower (right) ── */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 280px",gap:14,alignItems:"start"}}>

        {/* SHAP ATTRIBUTION */}
        {analysis?.shap?.top_drivers?.length > 0 && (
          <div className="glass" style={{padding:"18px 20px",borderRadius:16}}>
            <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 4px"}}>
              🔗 AI Risk Attribution (Top Drivers)
            </h3>
            <p style={{fontSize:14,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",marginBottom:14,marginTop:4}}>
              SHAP values: ↑ positive = increases default risk &nbsp;|&nbsp; ↓ negative = reduces risk
            </p>
            <div style={{display:"flex",flexDirection:"column",gap:1}}>
              {(analysis.shap.top_drivers||[]).slice(0,8).map((d,i)=>{
                const isRisk = d.shap_value > 0;
                const col    = isRisk ? "#ef4444" : "#10b981";
                return (
                  <div key={d.feature} style={{
                    display:"flex",alignItems:"center",justifyContent:"space-between",
                    padding:"9px 14px",borderRadius:8,
                    background: isDark ? (i%2===0?"rgba(255,255,255,0.025)":"transparent") : (i%2===0?"rgba(0,0,0,0.025)":"transparent"),
                    borderBottom: isDark ? "1px solid rgba(255,255,255,0.04)" : "1px solid rgba(0,0,0,0.05)",
                  }}>
                    <div style={{fontSize:16,fontWeight:500,color: isDark ? "#f1f5f9" : "#1E293B"}}>{d.feature.replace(/_/g," ")}</div>
                    <div style={{display:"flex",alignItems:"center",gap:10}}>
                      <span style={{fontSize:17,fontWeight:800,color:col,fontFamily:"monospace",minWidth:70,textAlign:"right"}}>
                        {d.shap_value>0?"+":""}{d.shap_value.toFixed(4)}
                      </span>
                      <span style={{fontSize:15,fontWeight:900,color:col,filter:`drop-shadow(0 0 4px ${col})`}}>
                        {isRisk?"↑":"↓"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* RIGHT COLUMN: Facility + Sector + Borrower */}
        <div style={{display:"flex",flexDirection:"column",gap:14}}>

          {/* PROPOSED FACILITY STRUCTURE */}
          {analysis?.decision?.loan_details && dec.verdict !== "REJECT" && (
            <div className="glass" style={{padding:"16px 18px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 14px"}}>
                Proposed Facility Structure
              </h3>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:9}}>
                {[
                  {l:"MAX FACILITY",  v:`₹${dec.loan_details?.max_loan_crore||"N/A"} Cr`},
                  {l:"INTEREST RATE", v:`${dec.loan_details?.interest_rate_pct||"N/A"}%`},
                  {l:"TENURE",        v:`${dec.loan_details?.tenure_years||"N/A"} yr`},
                  {l:"RISK PREMIUM",  v:`+${dec.loan_details?.risk_premium_pct||"N/A"}%`},
                ].map(({l,v})=>(
                  <div key={l} style={{padding:"10px 12px",borderRadius:10,background: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)",border:"1px solid rgba(236,91,19,0.1)"}}>
                    <div style={{fontSize:14,fontWeight:600,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:4}}>{l}</div>
                    <div style={{fontSize:19,fontWeight:800,color: isDark ? "#f1f5f9" : "#1E293B"}}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SECTOR PEER BENCHMARKING */}
          {sectorName && Object.keys(medians).length > 0 && (
            <div className="glass" style={{padding:"16px 18px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 14px"}}>
                Sector Peer Benchmarking{sectorName ? ` (${sectorName.charAt(0).toUpperCase()+sectorName.slice(1)})` : ""}
              </h3>
              <div style={{display:"flex",flexDirection:"column",gap:8}}>
                {[
                  {key:"dscr",           label:"DSCR",          fmt:v=>`${v.toFixed(2)}×`,        val:feat.dscr,           higher_better:true},
                  {key:"debt_to_equity", label:"Debt/Equity",   fmt:v=>`${v.toFixed(2)}×`,        val:feat.debt_to_equity, higher_better:false},
                  {key:"ebitda_margin",  label:"EBITDA Margin", fmt:v=>`${(v*100).toFixed(1)}%`,  val:feat.ebitda_margin,  higher_better:true},
                  {key:"current_ratio",  label:"Current Ratio", fmt:v=>`${v.toFixed(2)}×`,        val:feat.current_ratio,  higher_better:true},
                ].map(m=>{
                  const med = medians[m.key];
                  if (!med || !m.val) return null;
                  const better = m.higher_better ? m.val >= med : m.val <= med;
                  const col = better ? "#10b981" : "#ef4444";
                  return (
                    <div key={m.key} style={{
                      display:"flex",alignItems:"center",justifyContent:"space-between",
                      padding:"7px 10px",borderRadius:8,
                      background: isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)",
                      border: isDark ? "1px solid rgba(255,255,255,0.06)" : "1px solid rgba(0,0,0,0.06)",
                    }}>
                      <div style={{fontSize:16,color: isDark ? "rgba(255,255,255,0.6)" : "#64748B",fontWeight:500}}>{m.label}</div>
                      <div style={{
                        padding:"2px 10px",borderRadius:12,fontSize:14,fontWeight:700,
                        background:`${col}15`,color:col,border:`1px solid ${col}30`,
                      }}>{better?"Above peers":"Below peers"}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* BORROWER PROFILE */}
          {analysis?.decision?.company_name && (
            <div className="glass" style={{padding:"16px 18px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:800,color:"#ec5b13",textTransform:"uppercase",letterSpacing:"0.8px",margin:"0 0 12px"}}>
                🏢 Borrower Profile
              </h3>
              <div style={{display:"flex",flexDirection:"column",gap:8}}>
                {[
                  {l:"Company",    v:analysis.decision.company_name},
                  {l:"Risk Grade", v:analysis.decision.risk_grade||"N/A"},
                  {l:"Credit Score",v:`${(analysis.decision.credit_score||0).toFixed(1)}/100`},
                  {l:"PD",         v:`${((analysis.decision.probability_default||analysis.decision.probability_of_default||0)*100).toFixed(1)}%`},
                  {l:"Verdict",    v:(analysis.decision.verdict||"").replace(/_/g," ")},
                ].map(({l,v})=>(
                  <div key={l} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                    padding:"5px 0",borderBottom: isDark ? "1px solid rgba(255,255,255,0.05)" : "1px solid rgba(0,0,0,0.05)"}}>
                    <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",fontWeight:600,textTransform:"uppercase"}}>{l}</div>
                    <div style={{fontSize:16,fontWeight:700,color: isDark ? "#f1f5f9" : "#1E293B"}}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Final Recommendation ─────────────────────────── */}
      {analysis?.decision?.verdict && (
        <div className="glass" style={{
          padding:"26px 30px",borderRadius:16,
          borderColor:`${vColor}40`,boxShadow:`0 0 28px ${vColor}18`,
          background: isDark ? "rgba(16,10,5,0.92)" : "rgba(255,255,255,0.95)",
        }}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",gap:24,flexWrap:"wrap"}}>
            <div style={{flex:1,minWidth:260}}>
              <h3 style={{margin:"0 0 10px",fontSize:17,fontWeight:900,color: isDark ? "#f1f5f9" : "#1E293B",lineHeight:1.2}}>
                Final Recommendation: <span style={{color:vColor}}>{vLabel}</span>
              </h3>
              <p style={{margin:0,fontSize:16,color: isDark ? "#cbd5e1" : "#334155",lineHeight:1.7}}>
                {analysis.decision.reason || "Based on multi-dimensional analysis of financial, governance, and fraud signals."}
              </p>
              {(analysis.decision.conditions||[]).length > 0 && (
                <div style={{marginTop:14}}>
                  <div style={{fontSize:15,fontWeight:700,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:6}}>
                    Conditions Precedent
                  </div>
                  <ol style={{margin:0,paddingLeft:16,fontSize:16,color: isDark ? "#cbd5e1" : "#334155",lineHeight:1.8}}>
                    {(analysis.decision.conditions||[]).map((c,i)=><li key={i}>{c}</li>)}
                  </ol>
                </div>
              )}
            </div>
            <div style={{display:"flex",gap:12,flexShrink:0,alignItems:"flex-start",paddingTop:4}}>
              <button style={{
                padding:"11px 20px",borderRadius:10,fontSize:17,fontWeight:700,cursor:"pointer",
                background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
                border: isDark ? "1px solid rgba(255,255,255,0.15)" : "1px solid rgba(0,0,0,0.15)",
                color: isDark ? "#f1f5f9" : "#1E293B",letterSpacing:"0.3px",
              }}>Review Evidence</button>
              <button style={{
                padding:"11px 20px",borderRadius:10,fontSize:17,fontWeight:700,cursor:"pointer",
                background:vColor,border:`1px solid ${vColor}`,
                color:"#fff",letterSpacing:"0.3px",
                boxShadow:`0 4px 16px ${vColor}40`,
              }}>
                {dec.verdict==="APPROVE"?"Confirm Approve":dec.verdict==="CONDITIONAL_APPROVE"?"Confirm Conditional":"Confirm Reject"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

