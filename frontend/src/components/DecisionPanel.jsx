import React from "react";
import RiskRadar from "./RiskRadar";

const V_CFG = {
  APPROVE:             { label:"APPROVED",            color:"#10B981", glow:"glow-green", icon:"✅", bg:"rgba(16,185,129,.08)"  },
  CONDITIONAL_APPROVE: { label:"CONDITIONAL APPROVE", color:"#F59E0B", glow:"glow-amber", icon:"⚠️", bg:"rgba(245,158,11,.08)" },
  REJECT:              { label:"REJECTED",             color:"#EF4444", glow:"glow-red",   icon:"❌", bg:"rgba(239,68,68,.08)"  },
};

/* ── Horizontal SHAP bar component ──────────────────── */
function ShapBar({ feature, label, value, maxAbs }) {
  const isRisk = value > 0;
  const col  = isRisk ? "#EF4444" : "#10B981";
  const pct  = maxAbs > 0 ? Math.abs(value) / maxAbs * 100 : 0;
  return (
    <div style={{marginBottom:10}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:3,alignItems:"center"}}>
        <span style={{fontSize:10,color:"#94A3B8",flex:1,marginRight:8}}>{label || feature}</span>
        <span style={{fontSize:10,fontWeight:700,color:col,whiteSpace:"nowrap"}}>
          {isRisk?"↑ risk":"↓ risk"} {Math.abs(value*100).toFixed(1)}%
        </span>
      </div>
      <div style={{position:"relative",height:6,borderRadius:3,background:"rgba(30,41,59,.9)",overflow:"visible"}}>
        {/* Bar */}
        <div style={{
          position:"absolute",
          [isRisk?"left":"right"]: 0,
          height:"100%",borderRadius:3,
          background:`linear-gradient(${isRisk?"90deg":"270deg"},${col}60,${col})`,
          width:`${pct}%`,
          boxShadow:`0 0 8px ${col}50`,
          animation:"bar-grow .9s cubic-bezier(.4,0,.2,1) both",
          transition:"width .8s ease",
        }} />
      </div>
    </div>
  );
}

export default function DecisionPanel({ analysis, jobId }) {
  const dec   = analysis?.decision || {};
  const shap  = analysis?.shap     || {};
  const cfg   = V_CFG[dec.verdict] || V_CFG.REJECT;

  /* Build SHAP bars data */
  const shapFeatures = shap.top_features || [];
  const maxAbs = shapFeatures.length
    ? Math.max(...shapFeatures.map(f => Math.abs(f.shap_value || 0)))
    : 0;

  const handleDownload = () => window.open(`/api/cam/${jobId}/download`, "_blank");

  return (
    <div style={{maxWidth:1100,margin:"0 auto"}}>

      {/* ── Verdict Banner ─────────────────────────────── */}
      <div className={`glass ${cfg.glow} fade-in-up`} style={{
        padding:"28px 32px",borderRadius:20,marginBottom:20,
        borderColor:`${cfg.color}40`,
        background: cfg.bg,
        position:"relative",overflow:"hidden",
      }}>
        {/* Background glow orb */}
        <div style={{
          position:"absolute",top:-40,right:-40,width:200,height:200,borderRadius:"50%",
          background:`radial-gradient(circle,${cfg.color}20 0%,transparent 70%)`,
          pointerEvents:"none",
        }} />

        <div style={{display:"flex",alignItems:"flex-start",gap:20,flexWrap:"wrap"}}>
          {/* Verdict text */}
          <div style={{flex:1}}>
            <div style={{
              display:"inline-flex",alignItems:"center",gap:10,
              padding:"7px 18px",borderRadius:30,
              background:`${cfg.color}18`,border:`1.5px solid ${cfg.color}50`,
              marginBottom:14,
            }}>
              <div style={{
                width:9,height:9,borderRadius:"50%",background:cfg.color,
                animation:"pulse-dot 1.5s ease-in-out infinite",
                boxShadow:`0 0 10px ${cfg.color}`,
              }} />
              <span style={{fontSize:14,fontWeight:900,color:cfg.color,letterSpacing:"2px"}}>{cfg.label}</span>
            </div>

            <div style={{display:"flex",gap:20,alignItems:"baseline",marginBottom:12,flexWrap:"wrap"}}>
              <div>
                <span style={{fontSize:42,fontWeight:900,color:cfg.color,lineHeight:1}} className="num-pop">
                  {dec.credit_score || 0}
                </span>
                <span style={{fontSize:16,color:"#475569",marginLeft:4}}>/100</span>
              </div>
              <div style={{padding:"4px 12px",borderRadius:8,background:"rgba(255,255,255,.05)"}}>
                <span style={{fontSize:11,color:"#64748B"}}>Grade </span>
                <span style={{fontSize:16,fontWeight:800,color:cfg.color}}>{dec.risk_grade}</span>
              </div>
              <div style={{padding:"4px 12px",borderRadius:8,background:"rgba(255,255,255,.05)"}}>
                <span style={{fontSize:11,color:"#64748B"}}>Prob. of Default </span>
                <span style={{fontSize:14,fontWeight:700,color:cfg.color}}>
                  {((dec.probability_of_default||0)*100).toFixed(1)}%
                </span>
              </div>
            </div>

            <p style={{fontSize:12,color:"#94A3B8",lineHeight:1.7,maxWidth:580}}>{dec.reason}</p>
          </div>

          {/* Loan terms box */}
          {dec.loan_details?.max_loan_crore && (
            <div className="glass" style={{
              padding:"18px 22px",borderRadius:14,minWidth:200,
              borderColor:"rgba(16,185,129,.2)",
            }}>
              <div style={{fontSize:9,color:"#475569",textTransform:"uppercase",letterSpacing:"1px",marginBottom:12,fontWeight:600}}>
                Sanctioned Terms
              </div>
              {[
                {l:"Loan Limit",   v:`₹${dec.loan_details.max_loan_crore} Cr`,         c:"#10B981"},
                {l:"Rate",         v:`${dec.loan_details.interest_rate_pct}% p.a.`,     c:"#36cceb"},
                {l:"Tenure",       v:`${dec.loan_details.tenure_years} years`,           c:"#0ea5c9"},
                {l:"Risk Premium", v:`+${dec.loan_details.risk_premium_pct}%`,           c:"#F59E0B"},
              ].map(item=>(
                <div key={item.l} style={{marginBottom:8}}>
                  <div style={{fontSize:9,color:"#475569",marginBottom:1}}>{item.l}</div>
                  <div style={{fontSize:16,fontWeight:800,color:item.c}}>{item.v}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>

        {/* ── Left column ───────────────────────────────── */}
        <div style={{display:"flex",flexDirection:"column",gap:14}}>

          {/* Hard reject triggers */}
          {dec.hard_reject_flags?.length > 0 && (
            <div className="glass glow-red fade-in-up" style={{
              padding:"18px 20px",borderRadius:16,
              borderColor:"rgba(239,68,68,.3)",
            }}>
              <h3 style={{fontSize:11,fontWeight:700,color:"#EF4444",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                🚫 Hard Reject Triggers
              </h3>
              {dec.hard_reject_flags.map((f,i)=>(
                <div key={i} style={{
                  display:"flex",alignItems:"center",gap:8,
                  padding:"6px 10px",borderRadius:8,
                  background:"rgba(239,68,68,.08)",marginBottom:6,
                }}>
                  <div style={{width:4,height:4,borderRadius:"50%",background:"#EF4444",flexShrink:0}} />
                  <p style={{fontSize:11,color:"#FCA5A5",margin:0}}>{f.message || f}</p>
                </div>
              ))}
            </div>
          )}

          {/* Conditions precedent */}
          {dec.conditions?.length > 0 && (
            <div className="glass glow-amber fade-in-up" style={{
              padding:"18px 20px",borderRadius:16,
              borderColor:"rgba(245,158,11,.3)",
            }}>
              <h3 style={{fontSize:11,fontWeight:700,color:"#F59E0B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                📋 Conditions Precedent
              </h3>
              {dec.conditions.map((c,i)=>(
                <div key={i} style={{
                  display:"flex",alignItems:"flex-start",gap:8,marginBottom:8,
                  padding:"6px 10px",borderRadius:8,
                  background:"rgba(245,158,11,.06)",
                  borderLeft:"3px solid rgba(245,158,11,.5)",
                }}>
                  <span style={{fontSize:10,color:"#94A3B8",flex:1,lineHeight:1.5}}>{c}</span>
                </div>
              ))}
            </div>
          )}

          {/* Policy score deductions */}
          {dec.policy_flags?.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <h3 style={{fontSize:11,fontWeight:700,color:"#64748B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                Policy Score Deductions
              </h3>
              {dec.policy_flags.map((f,i)=>(
                <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                  padding:"5px 0",borderBottom:"1px solid rgba(255,255,255,.04)"}}>
                  <span style={{fontSize:10,color:"#64748B"}}>{f.rule}</span>
                  <span style={{fontSize:10,fontWeight:700,color:"#F87171"}}>−{f.deduction} pts</span>
                </div>
              ))}
              <div style={{display:"flex",justifyContent:"space-between",marginTop:10,paddingTop:10,
                borderTop:"1px solid rgba(54,204,235,.2)"}}>
                <span style={{fontSize:11,fontWeight:700,color:"#94A3B8"}}>Policy Score</span>
                <span style={{fontSize:14,fontWeight:800,color:"#36cceb"}}>{dec.policy_score}/100</span>
              </div>
            </div>
          )}

          {/* SHAP attribution */}
          {shapFeatures.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
                <h3 style={{fontSize:11,fontWeight:700,color:"#64748B",letterSpacing:"1px",textTransform:"uppercase",margin:0}}>
                  🔍 SHAP Risk Attribution
                </h3>
                <div style={{display:"flex",gap:12}}>
                  <div style={{display:"flex",alignItems:"center",gap:4}}>
                    <div style={{width:8,height:3,borderRadius:2,background:"#10B981"}} />
                    <span style={{fontSize:9,color:"#64748B"}}>Protective</span>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:4}}>
                    <div style={{width:8,height:3,borderRadius:2,background:"#EF4444"}} />
                    <span style={{fontSize:9,color:"#64748B"}}>Risk Driver</span>
                  </div>
                </div>
              </div>
              {shapFeatures.slice(0, 10).map((f, i)=>(
                <ShapBar key={i}
                  feature={f.feature}
                  label={f.description || f.feature}
                  value={f.shap_value || 0}
                  maxAbs={maxAbs}
                />
              ))}
            </div>
          )}

          {/* Human-readable SHAP fallback */}
          {shapFeatures.length === 0 && shap.human_readable?.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <h3 style={{fontSize:11,fontWeight:700,color:"#64748B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                🔍 SHAP Risk Attribution
              </h3>
              {shap.human_readable.map((line,i)=>(
                <p key={i} style={{fontSize:11,color:"#94A3B8",marginBottom:6,lineHeight:1.5}}>{line}</p>
              ))}
            </div>
          )}

          {/* Download button */}
          <button onClick={handleDownload} style={{
            padding:"14px",borderRadius:14,fontWeight:800,fontSize:13,
            color:"white",cursor:"pointer",border:"none",
            background:"linear-gradient(135deg,#36cceb,#0891b2)",
            boxShadow:"0 8px 30px rgba(54,204,235,.4)",
            transition:"transform .15s, box-shadow .15s",
          }}
            onMouseOver={e=>{e.target.style.transform="translateY(-2px)";e.target.style.boxShadow="0 12px 40px rgba(54,204,235,.6)";}} 
            onMouseOut={e=>{e.target.style.transform="translateY(0)";e.target.style.boxShadow="0 8px 30px rgba(54,204,235,.4)";}}
          >
            📄 Download Full CAM Report (PDF)
          </button>
        </div>

        {/* ── Right column: Risk Radar ──────────────────── */}
        <div>
          <RiskRadar analysis={analysis} />
        </div>
      </div>
    </div>
  );
}

