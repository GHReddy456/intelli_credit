import React from "react";
import RiskRadar from "./RiskRadar";

/* ── NLP helper: humanise raw flag messages ──────────── */
function nlpFlag(raw) {
  if (!raw || typeof raw !== "string") return raw;
  return raw
    .replace(/Hard reject:\s*/gi, "")
    .replace(/Litigation severity score exceeds threshold \(([0-9.]+) > ([0-9.]+)\)/i,
      (_,a,b)=>`Promoter / company litigation severity is critically high (score ${parseFloat(a).toFixed(2)}, acceptable limit: ${parseFloat(b).toFixed(2)}). Legal exposure must be resolved before sanction.`)
    .replace(/([a-z_]+) score exceeds threshold \(([0-9.]+) > ([0-9.]+)\)/gi,
      (_,name,a,b)=>`${name.replace(/_/g," ")} score is above the permissible ceiling (${parseFloat(a).toFixed(2)} vs limit ${parseFloat(b).toFixed(2)}).`)
    .replace(/([a-z_]+) below minimum \(([0-9.]+) < ([0-9.]+)\)/gi,
      (_,name,a,b)=>`${name.replace(/_/g," ")} is below the minimum threshold required (${parseFloat(a).toFixed(2)} vs minimum ${parseFloat(b).toFixed(2)}).`)
    .replace(/([a-z_]+) ratio exceeds ([0-9.]+)/gi,
      (_,name,v)=>`${name.replace(/_/g," ")} ratio is too high (${parseFloat(v).toFixed(2)}), indicating elevated financial risk.`);
}

const V_CFG = {
  APPROVE:             { label:"APPROVED",            color:"#10B981", glow:"glow-green", icon:"✅", bg:"rgba(16,185,129,.08)"  },
  CONDITIONAL_APPROVE: { label:"CONDITIONAL APPROVE", color:"#F59E0B", glow:"glow-amber", icon:"⚠️", bg:"rgba(245,158,11,.08)" },
  REJECT:              { label:"REJECTED",             color:"#EF4444", glow:"glow-red",   icon:"❌", bg:"rgba(239,68,68,.08)"  },
  REJECT_POLICY:       { label:"REJECTED (POLICY OVERRIDE)", color:"#EF4444", glow:"glow-red", icon:"🚫", bg:"rgba(239,68,68,.08)" },
};

/* ── Horizontal SHAP bar component ──────────────────── */
function ShapBar({ feature, label, value, maxAbs, isDark = true }) {
  const isRisk = value > 0;
  const col  = isRisk ? "#DC2626" : "#059669";
  const pct  = maxAbs > 0 ? Math.abs(value) / maxAbs * 100 : 0;
  return (
    <div style={{marginBottom:10}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:3,alignItems:"center"}}>
        <span style={{fontSize:16,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",flex:1,marginRight:8}}>{label || feature}</span>
        <span style={{fontSize:16,fontWeight:700,color:col,whiteSpace:"nowrap"}}>
          {isRisk?"↑ risk":"↓ risk"} {Math.abs(value*100).toFixed(1)}%
        </span>
      </div>
        <div style={{position:"relative",height:6,borderRadius:3,background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",overflow:"visible"}}>
        {/* Bar */}
        <div style={{
          position:"absolute",
          [isRisk?"left":"right"]: 0,
          height:"100%",borderRadius:3,
          background:`linear-gradient(${isRisk?"90deg":"270deg"},${col}80,${col})`,
          width:`${pct}%`,
          boxShadow:`0 0 6px ${col}40`,
          animation:"bar-grow .9s cubic-bezier(.4,0,.2,1) both",
          transition:"width .8s ease",
        }} />
      </div>
    </div>
  );
}

export default function DecisionPanel({ analysis, jobId, theme = "dark" }) {
  const isDark = theme !== "light";
  const dec   = analysis?.decision || {};
  const shap  = analysis?.shap     || {};
  const cfgKey = dec.verdict === "REJECT" && dec.hard_reject_flags?.length > 0 ? "REJECT_POLICY" : dec.verdict;
  const cfg   = V_CFG[cfgKey] || V_CFG.REJECT;

  /* Build SHAP bars data */
  const shapFeatures = shap.top_features || [];
  const maxAbs = shapFeatures.length
    ? Math.max(...shapFeatures.map(f => Math.abs(f.shap_value || 0)))
    : 0;

  const handleDownload = () => window.open(`/api/cam/${jobId}/download`, "_blank");

  return (
    <div>

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
              <span style={{fontSize:17,fontWeight:900,color:cfg.color,letterSpacing:"2px"}}>{cfg.label}</span>
            </div>

            <div style={{display:"flex",gap:20,alignItems:"baseline",marginBottom:12,flexWrap:"wrap"}}>
              <div>
                <span style={{fontSize:42,fontWeight:900,color:cfg.color,lineHeight:1}} className="num-pop">
                  {dec.credit_score || 0}
                </span>
                <span style={{fontSize:19,color: isDark ? "rgba(255,255,255,0.4)" : "#94A3B8",marginLeft:4}}>/100</span>
                {/* Confidence interval */}
                {dec.score_ci_low != null && dec.score_ci_high != null && (
                  <div style={{fontSize:16,color: isDark ? "rgba(255,255,255,0.4)" : "#94A3B8",marginTop:4,fontStyle:"italic"}}>
                    95% CI: {dec.score_ci_low.toFixed(1)} – {dec.score_ci_high.toFixed(1)}
                    {dec.score_std != null && ` (σ ${dec.score_std.toFixed(1)})`}
                  </div>
                )}
              </div>
              <div style={{padding:"4px 12px",borderRadius:8,background: isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)",border: isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)"}}>
                <span style={{fontSize:17,color: isDark ? "rgba(255,255,255,0.45)" : "#94A3B8"}}>Grade </span>
                <span style={{fontSize:19,fontWeight:800,color:cfg.color}}>{dec.risk_grade}</span>
              </div>
              <div style={{padding:"4px 12px",borderRadius:8,background: isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.05)",border: isDark ? "1px solid rgba(255,255,255,0.1)" : "1px solid rgba(0,0,0,0.1)"}}>
                <span style={{fontSize:17,color: isDark ? "rgba(255,255,255,0.45)" : "#94A3B8"}}>Prob. of Default </span>
                <span style={{fontSize:17,fontWeight:700,color:cfg.color}}>
                  {((dec.probability_of_default||0)*100).toFixed(1)}%
                </span>
              </div>
            </div>

            <p style={{fontSize:15,color: isDark ? "#cbd5e1" : "#334155",lineHeight:1.7,maxWidth:580}}>{nlpFlag(dec.reason) || dec.reason}</p>
          </div>

          {/* Loan terms box */}
          {dec.loan_details?.max_loan_crore && (
            <div className="glass" style={{
              padding:"18px 22px",borderRadius:14,minWidth:200,
              borderColor:"rgba(16,185,129,.2)",
            }}>
              <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",textTransform:"uppercase",letterSpacing:"1px",marginBottom:12,fontWeight:600}}>
                Sanctioned Terms
              </div>
              {[
                {l:"Loan Limit",   v:`₹${dec.loan_details.max_loan_crore} Cr`,         c:"#10B981"},
                {l:"Rate",         v:`${dec.loan_details.interest_rate_pct}% p.a.`,     c:"#0891b2"},
                {l:"Tenure",       v:`${dec.loan_details.tenure_years} years`,           c:"#059669"},
                {l:"Risk Premium", v:`+${dec.loan_details.risk_premium_pct}%`,           c:"#F59E0B"},
              ].map(item=>(
                <div key={item.l} style={{marginBottom:8}}>
                  <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.4)" : "#64748B",marginBottom:1}}>{item.l}</div>
                  <div style={{fontSize:19,fontWeight:800,color:item.c}}>{item.v}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Model Metrics Pills ───────────────────────── */}
      {analysis?.model_metrics?.roc_auc && (
        <div style={{marginBottom:16}}>
          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
            <span style={{fontSize:16,fontWeight:700,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",textTransform:"uppercase",letterSpacing:"0.8px"}}>Model Performance</span>
            <span style={{fontSize:14,fontWeight:700,padding:"2px 10px",borderRadius:20,background:"rgba(124,58,237,0.12)",border:"1px solid rgba(124,58,237,0.3)",color:"#7C3AED"}}>Prototype Model — Synthetic Training Data</span>
          </div>
          <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
          {[
            {label:"XGBoost AUC",     val:(analysis.model_metrics.roc_auc*100).toFixed(1)+"%",      col:"#059669"},
            {label:"F1 Score",        val:(analysis.model_metrics.f1_score*100).toFixed(1)+"%",      col:"#0891b2"},
            {label:"Precision",       val:(analysis.model_metrics.precision*100).toFixed(1)+"%",     col:"#7C3AED"},
            {label:"Recall",          val:(analysis.model_metrics.recall*100).toFixed(1)+"%",        col:"#D97706"},
            {label:"Test Accuracy",   val:(analysis.model_metrics.accuracy*100).toFixed(1)+"%",     col:"#16a34a"},
            {label:"Train Size",      val:String(analysis.model_metrics.train_size||"—"),           col:"#64748B"},
          ].map(p=>(
            <div key={p.label} style={{
              padding:"5px 12px",borderRadius:20,fontSize:16,fontWeight:700,
              background:`${p.col}12`,border:`1px solid ${p.col}30`,
              color:p.col,
            }}>
              {p.label}: <strong>{p.val}</strong>
            </div>
          ))}
          </div>
        </div>
      )}

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>

        {/* ── Left column ───────────────────────────────── */}
        <div style={{display:"flex",flexDirection:"column",gap:14}}>

          {/* Hard reject triggers */}
          {dec.hard_reject_flags?.length > 0 && (
            <div className="glass glow-red fade-in-up" style={{
              padding:"18px 20px",borderRadius:16,
              borderColor:"rgba(239,68,68,.3)",
            }}>
              <h3 style={{fontSize:17,fontWeight:700,color:"#EF4444",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                🚫 Hard Reject Triggers
              </h3>
              {dec.hard_reject_flags.map((f,i)=>(
                <div key={i} style={{
                  display:"flex",alignItems:"center",gap:8,
                  padding:"6px 10px",borderRadius:8,
                  background:"rgba(239,68,68,.08)",marginBottom:6,
                }}>
                  <div style={{width:4,height:4,borderRadius:"50%",background:"#EF4444",flexShrink:0}} />
                  <p style={{fontSize:17,color:"#fca5a5",margin:0,lineHeight:1.5}}>{nlpFlag(f.message || f)}</p>
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
              <h3 style={{fontSize:17,fontWeight:700,color:"#F59E0B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                📋 Conditions Precedent
              </h3>
              {dec.conditions.map((c,i)=>(
                <div key={i} style={{
                  display:"flex",alignItems:"flex-start",gap:8,marginBottom:8,
                  padding:"6px 10px",borderRadius:8,
                  background:"rgba(245,158,11,.06)",
                  borderLeft:"3px solid rgba(245,158,11,.5)",
                }}>
                  <span style={{fontSize:17,color:"#cbd5e1",flex:1,lineHeight:1.5}}>{c}</span>
                </div>
              ))}
            </div>
          )}

          {/* Policy score deductions */}
          {dec.policy_flags?.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:700,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                Policy Score Deductions
              </h3>
              {dec.policy_flags.map((f,i)=>(
                <div key={i} style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                  padding:"5px 0",borderBottom: isDark ? "1px solid rgba(255,255,255,.04)" : "1px solid rgba(0,0,0,.04)"}}>
                  <span style={{fontSize:16,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B"}}>{f.rule}</span>
                  <span style={{fontSize:16,fontWeight:700,color:"#F87171"}}>-{f.deduction} pts</span>
                </div>
              ))}
              <div style={{display:"flex",justifyContent:"space-between",marginTop:10,paddingTop:10,
                borderTop:"1px solid rgba(22,163,74,.2)"}}>
                <span style={{fontSize:17,fontWeight:700,color: isDark ? "#f1f5f9" : "#1E293B"}}>Policy Score</span>
                <span style={{fontSize:17,fontWeight:800,color:"#0891b2"}}>{dec.policy_score}/100</span>
              </div>
            </div>
          )}

          {/* Rule path: feature → rule → decision traceability */}
          {dec.rule_path?.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:700,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                Decision Rule Path
              </h3>
              {dec.rule_path.map((r,i)=>{
                const isHR = r.trigger === "HARD_REJECT";
                const col = isHR ? "#EF4444" : "#F59E0B";
                return (
                  <div key={i} style={{display:"flex",alignItems:"center",gap:8,
                    padding:"6px 10px",borderRadius:8,marginBottom:6,
                    background:`${col}08`,borderLeft:`3px solid ${col}50`}}>
                    <span style={{fontSize:16,fontWeight:700,color:col,minWidth:90}}>{r.trigger === "HARD_REJECT" ? "🚫 REJECT" : "⚠ DEDUCT"}</span>
                    <span style={{fontSize:16,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",flex:1}}>
                      {(r.feature||"").replace(/_/g," ")} → {r.message || r.trigger}
                    </span>
                    <span style={{fontSize:16,fontWeight:700,color:col,whiteSpace:"nowrap"}}>{r.impact}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* SHAP attribution */}
          {shapFeatures.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:16}}>
                <h3 style={{fontSize:17,fontWeight:700,color: isDark ? "rgba(255,255,255,0.5)" : "#64748B",letterSpacing:"1px",textTransform:"uppercase",margin:0}}>
                  🔍 SHAP Risk Attribution
                </h3>
                <div style={{display:"flex",gap:12}}>
                  <div style={{display:"flex",alignItems:"center",gap:4}}>
                    <div style={{width:8,height:3,borderRadius:2,background:"#10B981"}} />
                    <span style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B"}}>Protective</span>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:4}}>
                    <div style={{width:8,height:3,borderRadius:2,background:"#EF4444"}} />
                    <span style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B"}}>Risk Driver</span>
                  </div>
                </div>
              </div>
              {shapFeatures.slice(0, 10).map((f, i)=>(
                <ShapBar key={i}
                  feature={f.feature}
                  label={f.description || f.feature}
                  value={f.shap_value || 0}
                  maxAbs={maxAbs}
                  isDark={isDark}
                />
              ))}
            </div>
          )}

          {/* Human-readable SHAP fallback */}
          {shapFeatures.length === 0 && shap.human_readable?.length > 0 && (
            <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
              <h3 style={{fontSize:17,fontWeight:700,color:"rgba(255,255,255,0.5)",letterSpacing:"1px",marginBottom:12,textTransform:"uppercase"}}>
                🔍 SHAP Risk Attribution
              </h3>
              {shap.human_readable.map((line,i)=>(
                <p key={i} style={{fontSize:17,color: isDark ? "#cbd5e1" : "#334155",marginBottom:6,lineHeight:1.5}}>{line}</p>
              ))}
            </div>
          )}

          {/* Download button */}
          <button onClick={handleDownload} style={{
            padding:"14px",borderRadius:14,fontWeight:800,fontSize:19,
            color:"white",cursor:"pointer",border:"none",
            background:"linear-gradient(135deg,#16a34a,#059669)",
            boxShadow:"0 8px 30px rgba(22,163,74,.35)",
            transition:"transform .15s, box-shadow .15s",
          }}
            onMouseOver={e=>{e.target.style.transform="translateY(-2px)";e.target.style.boxShadow="0 12px 40px rgba(22,163,74,.55)";}} 
            onMouseOut={e=>{e.target.style.transform="translateY(0)";e.target.style.boxShadow="0 8px 30px rgba(22,163,74,.35)";}}
          >
            📄 Download Full CAM Report (PDF)
          </button>
        </div>

        {/* ── Right column: Risk Radar + Stress Test ───── */}
        <div style={{display:"flex",flexDirection:"column",gap:14}}>
          <RiskRadar analysis={analysis} />

          {/* Stress test panel */}
          {(() => {
            const feat = analysis?.features || {};
            const dec2 = analysis?.decision || {};
            if (!feat.dscr && !feat.debt_to_equity) return null;

            /* Scenario A: Revenue -20% → DSCR drops by 20% */
            const dscr_base   = feat.dscr || 0;
            const dscr_rev20  = +(dscr_base * 0.80).toFixed(2);
            const dscr_rate   = +(dscr_base * 0.88).toFixed(2);  /* +2% rate → ~12% DSCR erosion */
            const score_base  = dec2.credit_score || 0;
            const score_rev20 = Math.max(0, +(score_base * 0.88).toFixed(1));
            const score_rate  = Math.max(0, +(score_base * 0.94).toFixed(1));

            const scnColor = v => v >= 75 ? "#059669" : v >= 60 ? "#D97706" : "#DC2626";
            const scnLabel = v => v >= 75 ? "Approve" : v >= 60 ? "Conditional" : "Reject";

            return (
              <div className="glass fade-in-up" style={{padding:"18px 20px",borderRadius:16}}>
                <h3 style={{fontSize:17,fontWeight:800,color:"#7C3AED",letterSpacing:"1px",
                  textTransform:"uppercase",marginBottom:4}}>⚡ Stress Test Scenarios</h3>
                <p style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B",marginBottom:14,lineHeight:1.4}}>
                  Sensitivity analysis: impact of adverse macro shocks on credit score and DSCR.
                  <span style={{fontStyle:"italic",color: isDark ? "rgba(255,255,255,0.35)" : "#94A3B8"}}> Estimates use linear approximation — not full model re-run.</span>
                </p>
                <div style={{display:"flex",flexDirection:"column",gap:10}}>
                  {/* Base case */}
                  {[{
                    label:"Base Case",
                    desc:"Current financials",
                    dscr:dscr_base,
                    score:score_base,
                    base:true,
                  },{
                    label:"Revenue −20%",
                    desc:"Revenue contracts due to demand shock or sector stress",
                    dscr:dscr_rev20,
                    score:score_rev20,
                  },{
                    label:"Interest Rate +2%",
                    desc:"Rate hike of 200 bps increases debt servicing cost",
                    dscr:dscr_rate,
                    score:score_rate,
                  }].map(s=>(
                    <div key={s.label} style={{
                      padding:"10px 12px",borderRadius:10,
                      background: s.base ? "rgba(16,185,129,0.08)" : scnColor(s.score)+"0D",
                      border:`1.5px solid ${s.base ? "rgba(16,185,129,0.3)" : scnColor(s.score)+"40"}`,
                    }}>
                      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
                        <div>
                          <div style={{fontSize:16,fontWeight:800,color: isDark ? "#f1f5f9" : "#1E293B"}}>{s.label}</div>
                          <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B",marginTop:1}}>{s.desc}</div>
                        </div>
                        <div style={{textAlign:"right"}}>
                          <div style={{fontSize:21,fontWeight:900,color:scnColor(s.score),lineHeight:1}}>{s.score}</div>
                          <div style={{fontSize:14,fontWeight:700,color:scnColor(s.score)}}>{scnLabel(s.score)}</div>
                        </div>
                      </div>
                      <div style={{display:"flex",gap:14,marginTop:4}}>
                        <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B"}}>DSCR: <strong style={{color:s.dscr>=1.25?"#059669":"#DC2626"}}>{s.dscr.toFixed(2)}×</strong></div>
                        {!s.base && (
                          <div style={{fontSize:15,color: isDark ? "rgba(255,255,255,0.45)" : "#64748B"}}>Score drop: <strong style={{color:"#DC2626"}}>−{(score_base - s.score).toFixed(1)} pts</strong></div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

