import React, { useState, useCallback, useMemo } from "react";
import axios from "axios";
import Dashboard     from "./components/Dashboard";
import DecisionPanel from "./components/DecisionPanel";
import RiskRadar     from "./components/RiskRadar";
import FraudGraph    from "./components/FraudGraph";
import PromoterGraph from "./components/PromoterGraph";
import AgentReports  from "./components/AgentReports";
import EvidenceViewer from "./components/EvidenceViewer";
import CAMViewer     from "./components/CAMViewer";
import LLMSelector  from "./components/LLMSelector";

const API = axios.create({ baseURL: "/api" });

const TABS = [
  { id: "Dashboard",        icon: "◈", label: "Dashboard" },
  { id: "Decision",         icon: "⬡", label: "Decision" },
  { id: "Fraud Graph",      icon: "⬡", label: "Fraud Intel" },
  { id: "Promoter Network", icon: "◉", label: "Promoter Intel" },
  { id: "Agent Reports",    icon: "◈", label: "Agent Reports" },
  { id: "Evidence",         icon: "◈", label: "Evidence" },
  { id: "CAM",              icon: "◈", label: "CAM PDF" },
];

const PIPELINE_STEPS = [
  { label: "Parsing Documents",       icon: "📄", threshold: 10 },
  { label: "OCR & Segmentation",      icon: "🔍", threshold: 22 },
  { label: "Table Extraction",        icon: "📊", threshold: 34 },
  { label: "Cross-Verification",      icon: "✅", threshold: 46 },
  { label: "Fraud Detection",         icon: "🔒", threshold: 58 },
  { label: "Research & Web Intel",    icon: "🌐", threshold: 68 },
  { label: "Feature Engineering",     icon: "⚙️",  threshold: 78 },
  { label: "ML Credit Scoring",       icon: "🧠", threshold: 88 },
  { label: "Explainability (SHAP)",   icon: "📈", threshold: 94 },
  { label: "Generating CAM Report",   icon: "📋", threshold: 100 },
];

/* Fixed floating particle orbs */
const PARTICLES = [
  {x:8,   y:15, s:4, dur:20, dl:0,  c:"#36cceb"},
  {x:92,  y:10, s:3, dur:25, dl:3,  c:"#0ea5c9"},
  {x:50,  y:82, s:5, dur:18, dl:6,  c:"#36cceb"},
  {x:75,  y:60, s:3, dur:22, dl:1,  c:"#06b6d4"},
  {x:20,  y:50, s:4, dur:28, dl:9,  c:"#0ea5c9"},
  {x:88,  y:45, s:3, dur:16, dl:4,  c:"#36cceb"},
  {x:12,  y:75, s:5, dur:21, dl:7,  c:"#0891b2"},
  {x:60,  y:25, s:3, dur:26, dl:2,  c:"#0ea5c9"},
  {x:35,  y:8,  s:4, dur:23, dl:5,  c:"#36cceb"},
  {x:80,  y:90, s:3, dur:17, dl:8,  c:"#06b6d4"},
  {x:45,  y:40, s:4, dur:29, dl:1,  c:"#0891b2"},
  {x:5,   y:35, s:3, dur:19, dl:6,  c:"#36cceb"},
  {x:95,  y:70, s:5, dur:24, dl:3,  c:"#0ea5c9"},
  {x:25,  y:88, s:3, dur:21, dl:0,  c:"#0891b2"},
  {x:68,  y:5,  s:4, dur:18, dl:9,  c:"#36cceb"},
  {x:55,  y:55, s:3, dur:30, dl:4,  c:"#06b6d4"},
];

const DOC_SLOTS = [
  { key:"annual_report",  label:"Annual Report",  icon:"📊", desc:"FY 2022–24 · PDF",         accept:".pdf",         color:"#36cceb", bg:"#e0f9fd" },
  { key:"gstr3b",         label:"GSTR-3B",        icon:"🧾", desc:"Last 12 months returns",   accept:".pdf,.xlsx",   color:"#0891b2", bg:"#dbeafe" },
  { key:"bank_statement", label:"Bank Statement", icon:"🏦", desc:"6–12 months PDF",         accept:".pdf,.xlsx",   color:"#059669", bg:"#dcfce7" },
  { key:"itr6",           label:"ITR-6",          icon:"📋", desc:"Last 3 assessment years",  accept:".pdf,.xml",    color:"#D97706", bg:"#fef3c7" },
  { key:"legal_docs",     label:"Legal Docs",     icon:"⚖️",  desc:"MOA · AOA · Charges",      accept:".pdf,.doc,.docx",color:"#7C3AED", bg:"#ede9fe" },
];

export default function App() {
  const emptySlots = () => Object.fromEntries(DOC_SLOTS.map(s => [s.key, []]));
  const [docFiles,    setDocFiles]    = useState(emptySlots());
  const [companyName, setCompanyName] = useState("");
  const [jobId,       setJobId]       = useState(null);
  const [status,      setStatus]      = useState("idle");
  const [progress,    setProgress]    = useState(0);
  const [analysis,    setAnalysis]    = useState(null);
  const [activeTab,   setActiveTab]   = useState("Dashboard");
  const [dragOver,    setDragOver]    = useState(null);  // key of active slot
  const [phase,       setPhase]       = useState("");

  const currentStep = useMemo(() =>
    PIPELINE_STEPS.findLast?.(s => progress >= s.threshold - 12) ||
    PIPELINE_STEPS[0],
  [progress]);

  const addFiles = useCallback((key, incoming) => {
    setDocFiles(prev => ({ ...prev, [key]: [...prev[key], ...Array.from(incoming)] }));
  }, []);

  const removeFile = useCallback((key, idx) => {
    setDocFiles(prev => ({ ...prev, [key]: prev[key].filter((_,i) => i !== idx) }));
  }, []);

  const handleUpload = async () => {
    const allFiles = Object.values(docFiles).flat();
    if (!allFiles.length) return;
    setStatus("uploading"); setProgress(0);
    const fd = new FormData();
    allFiles.forEach(f => fd.append("files", f));
    fd.append("company_name", companyName.trim() || "Demo Company");
    try {
      const res = await API.post("/upload", fd);
      setJobId(res.data.job_id);
      setStatus("running");
      pollStatus(res.data.job_id);
    } catch { setStatus("error"); }
  };

  const pollStatus = (jid) => {
    const iv = setInterval(async () => {
      try {
        const res = await API.get(`/status/${jid}`);
        setProgress(res.data.progress || 0);
        setPhase(res.data.phase || "");
        if (res.data.status === "done") {
          clearInterval(iv); setStatus("done");
          const ar = await API.get(`/analysis/${jid}`);
          setAnalysis(ar.data);
        } else if (res.data.status === "error") {
          clearInterval(iv); setStatus("error");
        }
      } catch { clearInterval(iv); setStatus("error"); }
    }, 1500);
  };

  /* ── Status dot ───────────────────────────────────────── */
  const statusColor = {done:"#10B981", running:"#F59E0B", error:"#EF4444", idle:"#475569", uploading:"#F59E0B"};

  return (
    <div style={{ minHeight:"100vh", background:"var(--bg-deep)", position:"relative", overflow:"hidden" }}>

      {/* ── Floating particle background ─────────────────── */}
      <div style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:0 }}>
        {PARTICLES.map((p, i) => (
          <div key={i} style={{
            position:"absolute", left:`${p.x}%`, top:`${p.y}%`,
            width: p.s * 2, height: p.s * 2, borderRadius:"50%",
            background: p.c, opacity:.35,
            filter:`blur(${p.s + 2}px)`,
            animation:`float ${p.dur}s ease-in-out ${p.dl}s infinite`,
          }} />
        ))}
        {/* Large ambient orbs */}
        <div style={{position:"absolute",left:"20%",top:"30%",width:500,height:500,borderRadius:"50%",
          background:"radial-gradient(circle,rgba(54,204,235,.06) 0%,transparent 70%)",
          animation:"float 30s ease-in-out infinite"}} />
        <div style={{position:"absolute",right:"15%",bottom:"20%",width:400,height:400,borderRadius:"50%",
          background:"radial-gradient(circle,rgba(8,145,178,.07) 0%,transparent 70%)",
          animation:"float 25s ease-in-out 5s infinite"}} />
      </div>

      {/* ── Header ───────────────────────────────────────── */}
      <header className="glass" style={{
        position:"sticky",top:0,zIndex:50,
        padding:"12px 28px",
        borderBottom:"1px solid rgba(54,204,235,.22)",
        display:"flex",alignItems:"center",justifyContent:"space-between",
      }}>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          {/* Spinning hex logo */}
          <div style={{position:"relative",width:38,height:38}}>
            <div style={{
              position:"absolute",inset:0,
              border:"2px solid transparent",
              borderRadius:"12px",
              background:"linear-gradient(135deg,#36cceb,#0891b2) border-box",
              animation:"spin-slow 8s linear infinite",
            }} />
            <span style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>⬡</span>
          </div>
          <div>
            <div className="gradient-text" style={{fontSize:20,fontWeight:800,letterSpacing:"-0.5px"}}>
              Intelli-Credit
            </div>
            <div style={{fontSize:10,color:"#64748B",marginTop:-2}}>AI Corporate Credit Appraisal Engine</div>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:12}}>
          {/* LLM CPU / GPU selector */}
          <LLMSelector />
          {/* Pipeline status dot */}
          <div style={{display:"flex",alignItems:"center",gap:6}}>
            <div style={{
              width:8,height:8,borderRadius:"50%",
              background: statusColor[status] || "#475569",
              animation: status==="running" ? "pulse-dot 1.5s ease-in-out infinite" : "none",
              boxShadow: status==="running" ? "0 0 8px #F59E0B" : status==="done" ? "0 0 8px #10B981" : "none",
            }} />
            <span style={{fontSize:11,color:"#64748B",textTransform:"capitalize"}}>{status}</span>
          </div>
        </div>
      </header>

      {/* ── IDLE: Upload Zone ─────────────────────────────── */}
      {status === "idle" && (
        <div className="fade-in" style={{
          position:"relative",zIndex:1,
          maxWidth:1100,margin:"0 auto",
          padding:"36px 24px 48px",
        }}>

          {/* Hero */}
          <div style={{textAlign:"center",marginBottom:36}} className="fade-in-up">
            <div style={{
              fontSize:40,fontWeight:900,letterSpacing:"-1.5px",lineHeight:1.1,
              background:"linear-gradient(135deg,#0F172A 0%,#36cceb 60%,#0891b2 100%)",
              WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent",backgroundClip:"text",
            }}>AI Credit Appraisal<br/>in Minutes</div>
            <div style={{color:"#64748B",fontSize:14,marginTop:10}}>
              Upload each document type below → AI analyses everything → Instant CAM
            </div>
          </div>

          {/* Company name */}
          <div style={{maxWidth:480,margin:"0 auto 32px"}} className="fade-in-up">
            <label style={{display:"block",fontSize:11,fontWeight:700,color:"#475569",marginBottom:6,textTransform:"uppercase",letterSpacing:"0.8px"}}>
              Company Name
            </label>
            <input
              type="text"
              placeholder="e.g. TechGlobal Corp Pvt Ltd"
              value={companyName}
              onChange={e=>setCompanyName(e.target.value)}
              style={{
                width:"100%",padding:"12px 16px",borderRadius:12,
                border:"1.5px solid #E2E8F0",fontSize:14,color:"#0F172A",
                outline:"none",background:"#FFFFFF",
                boxShadow:"0 1px 4px rgba(0,0,0,.06)",
                transition:"border-color .15s, box-shadow .15s",
              }}
              onFocus={e=>{e.target.style.borderColor="#36cceb";e.target.style.boxShadow="0 0 0 3px rgba(54,204,235,.15)"; }}
              onBlur={e=>{e.target.style.borderColor="#E2E8F0";e.target.style.boxShadow="0 1px 4px rgba(0,0,0,.06)"; }}
            />
          </div>

          {/* 5 Document Slots */}
          <div style={{
            display:"grid",
            gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))",
            gap:16,marginBottom:28,
          }}>
            {DOC_SLOTS.map((slot, si) => {
              const slotFiles = docFiles[slot.key];
              const hasFiles  = slotFiles.length > 0;
              const isOver    = dragOver === slot.key;
              return (
                <div key={slot.key}
                  className="glass glass-hover"
                  style={{
                    borderRadius:16,overflow:"hidden",
                    border:`1.5px dashed ${isOver ? slot.color : hasFiles ? slot.color+"80" : "#E2E8F0"}`,
                    background: isOver ? slot.bg : "#FFFFFF",
                    transition:"all .2s ease",
                    animation:`fadeInUp .5s ease ${si*0.07}s both`,
                    position:"relative",
                  }}
                  onDrop={e=>{
                    e.preventDefault(); setDragOver(null);
                    addFiles(slot.key, e.dataTransfer.files);
                  }}
                  onDragOver={e=>{e.preventDefault(); setDragOver(slot.key);}}
                  onDragLeave={()=>setDragOver(null)}
                >
                  {/* Card header */}
                  <div style={{
                    padding:"14px 14px 10px",
                    borderBottom:`1px solid ${hasFiles ? slot.color+"30" : "#F1F5F9"}`,
                    background: hasFiles ? slot.bg+"88" : "#FAFAFA",
                    display:"flex",alignItems:"center",gap:10,
                  }}>
                    <div style={{
                      width:36,height:36,borderRadius:10,
                      background: slot.bg,
                      display:"flex",alignItems:"center",justifyContent:"center",
                      fontSize:18,flexShrink:0,
                    }}>{slot.icon}</div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{fontSize:12,fontWeight:700,color:"#1E293B",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>
                        {slot.label}
                      </div>
                      <div style={{fontSize:10,color:"#94A3B8",marginTop:1}}>{slot.desc}</div>
                    </div>
                    {hasFiles && (
                      <div style={{
                        width:20,height:20,borderRadius:"50%",
                        background:slot.color,
                        display:"flex",alignItems:"center",justifyContent:"center",
                        fontSize:9,color:"white",fontWeight:800,flexShrink:0,
                      }}>{slotFiles.length}</div>
                    )}
                  </div>

                  {/* Drop / browse area */}
                  <div style={{padding:"14px 12px"}}>
                    {slotFiles.length === 0 ? (
                      <div style={{textAlign:"center",padding:"10px 0"}}>
                        <div style={{fontSize:22,marginBottom:6,opacity:.5}}>⬆️</div>
                        <p style={{fontSize:11,color:"#94A3B8",marginBottom:10,lineHeight:1.4}}>
                          {isOver ? "Drop here!" : "Drag & drop or browse"}
                        </p>
                        <input
                          type="file" multiple accept={slot.accept}
                          id={`fup-${slot.key}`} className="hidden"
                          onChange={e=>addFiles(slot.key, e.target.files)}
                        />
                        <label htmlFor={`fup-${slot.key}`} style={{
                          display:"inline-block",padding:"7px 18px",borderRadius:8,cursor:"pointer",
                          fontSize:11,fontWeight:700,color:"white",
                          background:slot.color,
                          boxShadow:`0 2px 8px ${slot.color}50`,
                        }}>Browse</label>
                      </div>
                    ) : (
                      <div>
                        {slotFiles.map((f,fi)=>(
                          <div key={fi} style={{
                            display:"flex",alignItems:"center",gap:6,
                            padding:"5px 8px",borderRadius:8,marginBottom:4,
                            background:"#F8FAFC",border:"1px solid #E2E8F0",
                          }}>
                            <span style={{fontSize:12}}>📄</span>
                            <span style={{fontSize:10,color:"#334155",flex:1,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                              {f.name}
                            </span>
                            <button
                              onClick={()=>removeFile(slot.key,fi)}
                              style={{background:"none",border:"none",cursor:"pointer",color:"#CBD5E1",fontSize:14,lineHeight:1,padding:0,flexShrink:0}}
                              title="Remove"
                            >×</button>
                          </div>
                        ))}
                        {/* Add more */}
                        <input
                          type="file" multiple accept={slot.accept}
                          id={`fup-${slot.key}-more`} className="hidden"
                          onChange={e=>addFiles(slot.key, e.target.files)}
                        />
                        <label htmlFor={`fup-${slot.key}-more`} style={{
                          display:"block",textAlign:"center",marginTop:6,
                          padding:"5px",borderRadius:8,cursor:"pointer",
                          fontSize:10,fontWeight:600,color:slot.color,
                          border:`1px dashed ${slot.color}60`,
                        }}>+ Add more</label>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary + Run button */}
          {(() => {
            const totalFiles = Object.values(docFiles).flat().length;
            const filledSlots = DOC_SLOTS.filter(s => docFiles[s.key].length > 0).length;
            return (
              <div style={{maxWidth:480,margin:"0 auto"}} className="fade-in-up">
                {totalFiles > 0 && (
                  <div style={{
                    display:"flex",gap:8,flexWrap:"wrap",justifyContent:"center",marginBottom:16,
                  }}>
                    {DOC_SLOTS.filter(s=>docFiles[s.key].length>0).map(s=>(
                      <span key={s.key} style={{
                        fontSize:11,padding:"4px 12px",borderRadius:20,
                        background:s.bg,color:s.color,fontWeight:600,
                        border:`1px solid ${s.color}40`,
                      }}>✓ {s.label} ({docFiles[s.key].length})</span>
                    ))}
                  </div>
                )}
                <button
                  onClick={handleUpload}
                  disabled={totalFiles === 0}
                  style={{
                    width:"100%",padding:"15px",borderRadius:14,
                    fontWeight:800,fontSize:14,color:"white",cursor: totalFiles>0?"pointer":"not-allowed",
                    border:"none",letterSpacing:"0.3px",
                    background: totalFiles>0 ? "#36cceb" : "#CBD5E1",
                    boxShadow: totalFiles>0 ? "0 4px 18px rgba(54,204,235,.4)" : "none",
                    transition:"transform .15s, background .15s, box-shadow .15s",
                  }}
                  onMouseOver={e=>{ if(totalFiles>0){e.target.style.background="#1ab8d9";e.target.style.transform="translateY(-1px)"; }}}
                  onMouseOut={e=>{ if(totalFiles>0){e.target.style.background="#36cceb";e.target.style.transform="translateY(0)"; }}}
                >
                  {totalFiles===0
                    ? "Upload at least one document to continue"
                    : `🚀 Run Full AI Appraisal · ${totalFiles} file${totalFiles>1?"s":""} across ${filledSlots} category`+(filledSlots>1?"ies":"y")}
                </button>
              </div>
            );
          })()}
        </div>
      )}

      {/* ── PROCESSING ────────────────────────────────────── */}
      {(status==="uploading"||status==="running") && (
        <div className="fade-in" style={{
          position:"relative",zIndex:1,
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"flex-start",
          minHeight:"calc(100vh - 62px)", padding:"40px 24px",
        }}>
          {/* Title */}
          <div style={{textAlign:"center",marginBottom:32}}>
            <div className="gradient-text" style={{fontSize:26,fontWeight:900,marginBottom:6}}>
              AI Pipeline Running
            </div>
            <div style={{fontSize:13,color:"#64748B"}}>
              {currentStep?.icon} {currentStep?.label || "Initialising…"} &nbsp;·&nbsp; {progress}% complete
            </div>
          </div>

          {/* ── Pipeline Flow Diagram ─────────────────────── */}
          <div style={{width:"100%",maxWidth:900,marginBottom:32}}>
            {/* Row 1: steps 1-5 */}
            {[PIPELINE_STEPS.slice(0,5), PIPELINE_STEPS.slice(5,10)].map((row, ri) => (
              <div key={ri} style={{marginBottom: ri===0 ? 8 : 0}}>
                <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:0}}>
                  {row.map((s, i) => {
                    const globalIdx = ri*5 + i;
                    const done   = progress >= s.threshold;
                    const active = !done && progress >= (PIPELINE_STEPS[globalIdx-1]?.threshold||0);
                    const bg     = done ? "linear-gradient(135deg,#10B981,#059669)"
                                 : active ? "linear-gradient(135deg,#36cceb,#0891b2)"
                                 : "#FFFFFF";
                    const shadow = done   ? "0 4px 16px rgba(16,185,129,.45)"
                                 : active ? "0 4px 20px rgba(54,204,235,.55)"
                                 : "0 2px 8px rgba(0,0,0,.06)";
                    const labelColor = done ? "#059669" : active ? "#0891b2" : "#94A3B8";
                    return (
                      <React.Fragment key={s.label}>
                        <div style={{display:"flex",flexDirection:"column",alignItems:"center",width:140}}>
                          {/* Circle icon */}
                          <div style={{
                            width:56,height:56,borderRadius:"50%",
                            background: bg,
                            boxShadow: shadow,
                            display:"flex",alignItems:"center",justifyContent:"center",
                            fontSize:22,marginBottom:8,
                            border: active ? "2px solid #36cceb" : done ? "2px solid #10B981" : "2px solid #e2e8f0",
                            animation: active ? "glow-blue 1.5s ease-in-out infinite" : "none",
                            transition:"all .4s ease",
                            position:"relative",
                          }}>
                            {done ? "✓" : s.icon}
                            {active && (
                              <div style={{
                                position:"absolute",inset:-4,borderRadius:"50%",
                                border:"2px solid #36cceb",opacity:.5,
                                animation:"spin-slow 2s linear infinite",
                              }} />
                            )}
                          </div>
                          {/* Label */}
                          <div style={{
                            fontSize:9.5,fontWeight:600,color:labelColor,
                            textAlign:"center",lineHeight:1.3,maxWidth:100,
                            transition:"color .4s ease",
                          }}>{s.label}</div>
                          {done && <div style={{fontSize:8,color:"#10B981",marginTop:2,fontWeight:700}}>DONE ✓</div>}
                          {active && <div style={{fontSize:8,color:"#36cceb",marginTop:2,fontWeight:700,animation:"pulse-dot 1.2s ease infinite"}}>RUNNING…</div>}
                        </div>
                        {/* Arrow between steps */}
                        {i < row.length-1 && (
                          <div style={{
                            flex:0,width:24,height:2,
                            background: progress >= row[i+1]?.threshold ? "#10B981"
                                      : progress >= s.threshold ? "#36cceb" : "#e2e8f0",
                            position:"relative",marginBottom:28,transition:"background .6s ease",
                          }}>
                            <div style={{
                              position:"absolute",right:-4,top:"50%",transform:"translateY(-50%)",
                              width:0,height:0,
                              borderLeft:`6px solid ${progress >= s.threshold ? "#36cceb" : "#e2e8f0"}`,
                              borderTop:"4px solid transparent",
                              borderBottom:"4px solid transparent",
                              transition:"border-color .6s ease",
                            }} />
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
                {/* Connector between row 1 and row 2 */}
                {ri===0 && (
                  <div style={{display:"flex",justifyContent:"flex-end",paddingRight:70}}>
                    <div style={{
                      width:2,height:20,
                      background: progress >= PIPELINE_STEPS[5].threshold ? "#10B981" : progress >= PIPELINE_STEPS[4].threshold ? "#36cceb" : "#e2e8f0",
                      margin:"0 auto",transition:"background .6s ease",
                    }} />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* ── Progress bar ───────────────────────────────── */}
          <div style={{width:500,maxWidth:"90vw",marginBottom:24}}>
            <div style={{height:8,borderRadius:4,background:"#e2e8f0",overflow:"hidden",marginBottom:6}}>
              <div style={{
                height:"100%",borderRadius:4,
                background:"linear-gradient(90deg,#36cceb,#0891b2)",
                width:`${progress}%`,
                transition:"width .8s ease",
                boxShadow:"0 0 12px rgba(54,204,235,.5)",
              }} />
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"#94A3B8"}}>
              <span style={{fontWeight:600}}>{progress}% complete</span>
              <span>{PIPELINE_STEPS.filter(s=>progress>=s.threshold).length}/{PIPELINE_STEPS.length} steps done</span>
            </div>
          </div>

          {/* Shimmer placeholder */}
          <div style={{width:500,maxWidth:"90vw"}}>
            {[1,2,3].map(i=>(
              <div key={i} className="shimmer-bar" style={{height:12,borderRadius:6,marginBottom:8,opacity:.5,width:`${90-i*12}%`}} />
            ))}
          </div>

          {/* Spinning rings — keep hidden element at bottom to avoid code break */}
          <div style={{display:"none",position:"relative",width:120,height:120,marginBottom:36}}>
            <div style={{
              position:"absolute",inset:0,borderRadius:"50%",
              border:"2px solid transparent",
              borderTopColor:"#36cceb",
              animation:"spin-slow 1.2s linear infinite",
            }} />
            <div style={{
              position:"absolute",inset:10,borderRadius:"50%",
              border:"2px solid transparent",
              borderTopColor:"#0ea5c9",
              animation:"spin-slower 1.8s linear infinite",
            }} />
            <div style={{
              position:"absolute",inset:22,borderRadius:"50%",
              border:"2px solid transparent",
              borderTopColor:"#059669",
              animation:"spin-slow 2.4s linear infinite",
            }} />
            <div style={{
              position:"absolute",inset:0,
              display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:28,
            }}>🧠</div>
          </div>

          <div className="gradient-text" style={{fontSize:22,fontWeight:800,marginBottom:6}}>
            Analysing Documents
          </div>
          <div style={{fontSize:13,color:"#475569",marginBottom:32,textAlign:"center"}}>
            {currentStep?.icon} {currentStep?.label || "Initialising…"}
          </div>

          {/* Progress bar */}
          <div style={{width:360,maxWidth:"90vw"}}>
            <div style={{
              height:6,borderRadius:3,
              background:"rgba(0,0,0,.07)",
              overflow:"hidden",marginBottom:8,
            }}>
              <div style={{
                height:"100%",borderRadius:3,
                background:"linear-gradient(90deg,#36cceb,#0891b2)",
                width:`${progress}%`,
                transition:"width .6s ease",
                boxShadow:"0 0 12px rgba(54,204,235,.6)",
              }} />
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"#475569"}}>
              <span>{progress}% complete</span>
              <span>{PIPELINE_STEPS.filter(s=>progress>=s.threshold).length}/{PIPELINE_STEPS.length} steps</span>
            </div>
          </div>

          {/* Step checklist */}
          <div style={{marginTop:28,display:"flex",flexDirection:"column",gap:6,width:320,maxWidth:"85vw"}}>
            {PIPELINE_STEPS.map((s,i) => {
              const done = progress >= s.threshold;
              const active = !done && progress >= (PIPELINE_STEPS[i-1]?.threshold||0);
              return (
                <div key={s.label} className="glass" style={{display:"none"}}></div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── RESULTS ───────────────────────────────────────── */}
      {status==="done" && analysis && (
        <div style={{position:"relative",zIndex:1}}>
          {/* Tab bar */}
          <div className="glass" style={{
            display:"flex",gap:4,padding:"8px 24px 0",
            position:"sticky",top:62,zIndex:40,
            borderBottom:"1px solid rgba(54,204,235,.18)",
            overflowX:"auto",
          }}>
            {TABS.map(t => (
              <button key={t.id} onClick={()=>setActiveTab(t.id)} style={{
                padding:"8px 16px",borderRadius:"10px 10px 0 0",
                fontSize:12,fontWeight:600,cursor:"pointer",border:"none",
                whiteSpace:"nowrap",
                background: activeTab===t.id ? "rgba(54,204,235,.12)" : "transparent",
                color: activeTab===t.id ? "#0891b2" : "#475569",
                borderBottom: activeTab===t.id ? "2px solid #36cceb" : "2px solid transparent",
                boxShadow: activeTab===t.id ? "0 0 16px rgba(54,204,235,.15)" : "none",
                transition:"all .25s ease",
              }}>
                {t.label}
              </button>
            ))}
          </div>

          <div className="fade-in" style={{padding:24}} key={activeTab}>
            {activeTab==="Dashboard"        && <Dashboard    analysis={analysis} />}
            {activeTab==="Decision"         && <DecisionPanel analysis={analysis} jobId={jobId} />}
            {activeTab==="Fraud Graph"      && <FraudGraph   analysis={analysis} />}
            {activeTab==="Promoter Network" && <PromoterGraph analysis={analysis} />}
            {activeTab==="Agent Reports"    && <AgentReports  analysis={analysis} />}
            {activeTab==="Evidence"         && <EvidenceViewer analysis={analysis} />}
            {activeTab==="CAM"              && <CAMViewer     jobId={jobId} />}
          </div>
        </div>
      )}

      {/* ── ERROR ─────────────────────────────────────────── */}
      {status==="error" && (
        <div className="fade-in" style={{
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
          minHeight:"calc(100vh - 62px)",
        }}>
          <div style={{fontSize:56,marginBottom:16,filter:"drop-shadow(0 0 20px rgba(239,68,68,.5))"}}>❌</div>
          <p style={{color:"#F87171",fontSize:16,fontWeight:600,marginBottom:8}}>Processing failed</p>
          <p style={{color:"#475569",fontSize:13,marginBottom:24}}>Check that valid PDF documents were uploaded</p>
          <button onClick={()=>{setStatus("idle");setDocFiles(emptySlots());setProgress(0);}} style={{
            padding:"10px 24px",borderRadius:10,fontSize:13,fontWeight:600,
            color:"white",background:"rgba(239,68,68,.2)",border:"1px solid rgba(239,68,68,.4)",cursor:"pointer",
          }}>↩ Try Again</button>
        </div>
      )}
    </div>
  );
}

