import React, { useState, useEffect } from "react";

const FIVE_CS = ["character","capacity","capital","collateral","conditions"];

/* ── Animated SVG Score Gauge ────────────────────────── */
function AnimGauge({ score }) {
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
      <circle cx="90" cy="90" r={R} fill="none" stroke="rgba(30,41,59,.9)" strokeWidth="14" />
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
      <text x="90" y="110" textAnchor="middle" fontSize="10" fill="#64748B" fontWeight="600">
        CREDIT SCORE
      </text>
    </svg>
  );
}

/* ── Glowing Metric Card ─────────────────────────────── */
function MetricCard({ label, value, sub, tone, delay = 0 }) {
  const palettes = {
    green: { text:"#10B981", glow:"0 0 24px rgba(16,185,129,.35)", border:"rgba(16,185,129,.25)" },
    amber: { text:"#F59E0B", glow:"0 0 24px rgba(245,158,11,.35)", border:"rgba(245,158,11,.25)" },
    red:   { text:"#EF4444", glow:"0 0 24px rgba(239,68,68,.35)",  border:"rgba(239,68,68,.25)"  },
    blue:  { text:"#36cceb", glow:"0 0 18px rgba(54,204,235,.25)", border:"rgba(54,204,235,.2)"  },
  };
  const p = palettes[tone] || palettes.blue;
  return (
    <div className="glass glass-hover" style={{
      padding:"18px 14px", borderRadius:14, textAlign:"center",
      borderColor: p.border, boxShadow: p.glow,
      animation:`fadeInUp .55s ease ${delay}s both`,
    }}>
      <p style={{fontSize:9,color:"#475569",marginBottom:6,textTransform:"uppercase",letterSpacing:"0.8px",fontWeight:600}}>
        {label}
      </p>
      <p style={{fontSize:21,fontWeight:800,color:p.text,lineHeight:1}}>{value}</p>
      {sub && <p style={{fontSize:9,color:"#475569",marginTop:4}}>{sub}</p>}
    </div>
  );
}

export default function Dashboard({ analysis }) {
  const dec   = analysis?.decision  || {};
  const feat  = analysis?.features  || {};
  const fraud = analysis?.fraud     || {};
  const fiveCs = dec.five_cs_scores || {};

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

  return (
    <div style={{maxWidth:1100,margin:"0 auto"}}>

      {/* ── Row 1: Gauge + Verdict ─────────────────────── */}
      <div style={{display:"flex",flexDirection:"column",gap:16,marginBottom:20}}
        className="fade-in-up"
      >
        <div style={{display:"grid",gridTemplateColumns:"auto 1fr",gap:16,alignItems:"stretch"}}>

          {/* Gauge card */}
          <div className={`glass ${gCls}`} style={{
            padding:"28px 24px",borderRadius:20,
            display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
            minWidth:220,
          }}>
            <AnimGauge score={score} />
            <div style={{marginTop:10,textAlign:"center"}}>
              <span style={{fontSize:12,color:"#64748B",fontWeight:500}}>Risk Grade</span>
              <span style={{
                marginLeft:8,fontSize:14,fontWeight:800,
                color: vColor,
              }}>{dec.risk_grade || "—"}</span>
            </div>
          </div>

          {/* Verdict banner */}
          <div className={`glass ${gCls}`} style={{
            padding:"28px 28px",borderRadius:20,
            borderColor: vColor+"50",
          }}>
            <div style={{
              display:"inline-flex",alignItems:"center",gap:10,marginBottom:14,
              padding:"6px 16px",borderRadius:30,
              background:`${vColor}18`,border:`1.5px solid ${vColor}40`,
            }}>
              <div style={{
                width:8,height:8,borderRadius:"50%",background:vColor,
                animation:"pulse-dot 1.5s ease-in-out infinite",
                boxShadow:`0 0 8px ${vColor}`,
              }} />
              <span style={{fontSize:13,fontWeight:800,color:vColor,letterSpacing:"1px"}}>{vLabel}</span>
            </div>

            <p style={{fontSize:12,color:"#94A3B8",lineHeight:1.6,marginBottom:16}}>{dec.reason}</p>

            {dec.loan_details?.max_loan_crore && (
              <div style={{display:"flex",gap:20,flexWrap:"wrap"}}>
                {[
                  {l:"Loan Limit",v:`₹${dec.loan_details.max_loan_crore} Cr`,c:"#10B981"},
                  {l:"Interest Rate",v:`${dec.loan_details.interest_rate_pct}%`,c:"#36cceb"},
                  {l:"Tenure",v:`${dec.loan_details.tenure_years} yr`,c:"#0ea5c9"},
                  {l:"Risk Premium",v:`+${dec.loan_details.risk_premium_pct}%`,c:"#F59E0B"},
                ].map(item=>(
                  <div key={item.l}>
                    <div style={{fontSize:9,color:"#475569",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:2}}>{item.l}</div>
                    <div style={{fontSize:20,fontWeight:800,color:item.c}} className="num-pop">{item.v}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Row 2: 8 Metric cards ─────────────────────── */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,marginBottom:20}}>
        <MetricCard label="DSCR"              value={`${(feat.dscr||0).toFixed(2)}×`}  tone={dscrTone}  delay={0}   />
        <MetricCard label="Debt / Equity"     value={`${(feat.debt_to_equity||0).toFixed(2)}×`} tone={deTone}  delay={0.05}/>
        <MetricCard label="Current Ratio"     value={`${(feat.current_ratio||0).toFixed(2)}×`} tone={crTone}  delay={0.1} />
        <MetricCard label="EBITDA Margin"     value={`${((feat.ebitda_margin||0)*100).toFixed(1)}%`} tone={ebtTone}  delay={0.15}/>
        <MetricCard label="Int. Coverage"     value={`${(feat.interest_coverage_ratio||0).toFixed(2)}×`} tone={dscrTone} delay={0.2} />
        <MetricCard label="Fraud Risk"        value={`${(fraud.fraud_risk_score||0).toFixed(0)}/100`} tone={fraudTone} delay={0.25} sub="lower=better"/>
        <MetricCard label="Litigation Cases"  value={feat.litigation_count || 0} tone={(feat.litigation_count||0)===0?"green":"red"} delay={0.3} />
        <MetricCard label="Prob. of Default"  value={`${((dec.probability_of_default||0)*100).toFixed(1)}%`} tone={pdTone}  delay={0.35}/>
      </div>

      {/* ── Row 3: Five Cs ────────────────────────────── */}
      <div className="glass" style={{padding:"22px 24px",borderRadius:20}}>
        <h3 style={{
          fontSize:11,fontWeight:700,letterSpacing:"1.5px",textTransform:"uppercase",
          color:"#475569",marginBottom:18,
        }}>Five Cs Assessment</h3>
        <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:20}}>
          {FIVE_CS.map((c,i) => {
            const sc  = fiveCs[c] || 0;
            const col = sc >= 70 ? "#10B981" : sc >= 50 ? "#F59E0B" : "#EF4444";
            return (
              <div key={c}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:6}}>
                  <span style={{fontSize:10,fontWeight:600,color:"#94A3B8",textTransform:"capitalize"}}>{c}</span>
                  <span style={{fontSize:14,fontWeight:800,color:col}}>{sc.toFixed(0)}</span>
                </div>
                {/* Vertical bar */}
                <div style={{position:"relative",height:90,width:"100%",background:"rgba(30,41,59,.8)",borderRadius:6,overflow:"hidden"}}>
                  <div style={{
                    position:"absolute",bottom:0,left:0,right:0,
                    background:`linear-gradient(0deg,${col}99,${col})`,
                    borderRadius:6,
                    height:`${sc}%`,
                    boxShadow:`0 -4px 16px ${col}50`,
                    transition:"height 1s cubic-bezier(.4,0,.2,1)",
                    animation:`bar-grow .9s cubic-bezier(.4,0,.2,1) ${0.1+i*0.12}s both`,
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}

