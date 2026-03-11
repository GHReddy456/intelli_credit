import React, { useState, useCallback, useMemo, useEffect, useRef } from "react";
import axios from "axios";
import HomePage      from "./components/HomePage";
import UploadPage   from "./components/UploadPage";
import Dashboard     from "./components/Dashboard";
import DecisionPanel from "./components/DecisionPanel";
import RiskRadar     from "./components/RiskRadar";
import FraudGraph    from "./components/FraudGraph";
import PromoterGraph from "./components/PromoterGraph";
import AgentReports  from "./components/AgentReports";
import EvidenceViewer from "./components/EvidenceViewer";
import CAMViewer     from "./components/CAMViewer";
import LLMSelector  from "./components/LLMSelector";
import ClassificationReview from "./components/ClassificationReview";
import SchemaEditor from "./components/SchemaEditor";

/* ── Load Material Symbols font (same as Home/Upload pages) ─────── */
function useMaterialFont() {
  useEffect(() => {
    [
      ["app-font-ps", "https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;800;900&display=swap"],
      ["app-font-ms", "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"],
    ].forEach(([id, href]) => {
      if (!document.getElementById(id)) {
        const l = document.createElement("link");
        l.id = id; l.rel = "stylesheet"; l.href = href;
        document.head.appendChild(l);
      }
    });
  }, []);
}
function MSIcon({ n, style = {} }) {
  return <span className="material-symbols-outlined" style={{ userSelect:"none", lineHeight:1, ...style }}>{n}</span>;
}

const API = axios.create({ baseURL: "/api" });

const TABS = [
  { id: "Dashboard",        icon: "◈", label: "Dashboard" },
  { id: "Decision",         icon: "⬡", label: "Decision" },
  { id: "Fraud Graph",      icon: "⬡", label: "Fraud Intel" },
  { id: "Promoter Network", icon: "◉", label: "Promoter Intel" },
  { id: "Agent Reports",    icon: "◈", label: "Agent Reports" },
  { id: "Evidence",         icon: "◈", label: "Evidence" },
  { id: "CAM",              icon: "◈", label: "CAM PDF" },
  { id: "Schema",           icon: "⚙", label: "Schema Editor" },
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
  {x:8,   y:15, s:4, dur:20, dl:0,  c:"#ec5b13"},
  {x:92,  y:10, s:3, dur:25, dl:3,  c:"rgba(54,204,235,0.85)"},
  {x:50,  y:82, s:5, dur:18, dl:6,  c:"#ec5b13"},
  {x:75,  y:60, s:3, dur:22, dl:1,  c:"rgba(54,204,235,0.7)"},
  {x:20,  y:50, s:4, dur:28, dl:9,  c:"#d4420a"},
  {x:88,  y:45, s:3, dur:16, dl:4,  c:"#ec5b13"},
  {x:12,  y:75, s:5, dur:21, dl:7,  c:"rgba(8,145,178,0.8)"},
  {x:60,  y:25, s:3, dur:26, dl:2,  c:"#f97316"},
  {x:35,  y:8,  s:4, dur:23, dl:5,  c:"#ec5b13"},
  {x:80,  y:90, s:3, dur:17, dl:8,  c:"rgba(54,204,235,0.75)"},
  {x:45,  y:40, s:4, dur:29, dl:1,  c:"#d4420a"},
  {x:5,   y:35, s:3, dur:19, dl:6,  c:"rgba(8,145,178,0.7)"},
  {x:95,  y:70, s:5, dur:24, dl:3,  c:"#ec5b13"},
  {x:25,  y:88, s:3, dur:21, dl:0,  c:"#f97316"},
  {x:68,  y:5,  s:4, dur:18, dl:9,  c:"#ec5b13"},
  {x:55,  y:55, s:3, dur:30, dl:4,  c:"rgba(54,204,235,0.8)"},
];

const DOC_SLOTS = [
  { key:"annual_report",        label:"Annual Report",        icon:"📊", desc:"FY 2022–24 · PDF",         accept:".pdf",            color:"#a855f7", bg:"#f3e8ff" },
  { key:"alm",                  label:"ALM Statement",        icon:"🏦", desc:"Asset-Liability Maturity", accept:".pdf,.xlsx",      color:"#0891b2", bg:"#dbeafe" },
  { key:"shareholding_pattern", label:"Shareholding Pattern", icon:"📈", desc:"Promoter / Public / FII",  accept:".pdf,.xlsx",      color:"#059669", bg:"#dcfce7" },
  { key:"borrowing_profile",    label:"Borrowing Profile",    icon:"📋", desc:"Debt structure & covenants",accept:".pdf,.xlsx",     color:"#D97706", bg:"#fef3c7" },
  { key:"portfolio_performance",label:"Portfolio Performance",icon:"📉", desc:"Portfolio cuts & returns", accept:".pdf,.xlsx",      color:"#7C3AED", bg:"#ede9fe" },
  { key:"gstr3b",               label:"GSTR-3B",              icon:"🧾", desc:"Last 12 months returns",   accept:".pdf,.xlsx",      color:"#60a5fa", bg:"#dbeafe" },
  { key:"bank_statement",       label:"Bank Statement",       icon:"💰", desc:"6–12 months PDF",         accept:".pdf,.xlsx",      color:"#4ade80", bg:"#dcfce7" },
  { key:"itr6",                 label:"ITR-6",                icon:"📝", desc:"Last 3 assessment years",  accept:".pdf,.xml",       color:"#fb923c", bg:"#fef3c7" },
  { key:"legal_docs",           label:"Legal Docs",           icon:"⚖️",  desc:"MOA · AOA · Charges",      accept:".pdf,.doc,.docx", color:"#f87171", bg:"#ede9fe" },
];

export default function App() {
  useMaterialFont();
  const emptySlots = () => Object.fromEntries(DOC_SLOTS.map(s => [s.key, []]));
  const [page,        setPage]        = useState("home");  // "home" | "upload" | "classify" | "app"
  const [theme,       setTheme]       = useState("dark");  // "dark" | "light"
  const [docFiles,    setDocFiles]    = useState(emptySlots());
  const [companyName, setCompanyName] = useState("");
  const [entityDetails, setEntityDetails] = useState({});
  const [loanDetails,   setLoanDetails]   = useState({});
  const [classifications, setClassifications] = useState([]);

  /* ── Sync theme → body class ──────────────────────────── */
  useEffect(() => {
    document.body.classList.toggle("lt-mode", theme === "light");
  }, [theme]);
  const [jobId,       setJobId]       = useState(null);
  const [status,      setStatus]      = useState("idle");
  const [progress,    setProgress]    = useState(0);
  const [analysis,    setAnalysis]    = useState(null);
  const [activeTab,   setActiveTab]   = useState("Dashboard");
  const [dragOver,    setDragOver]    = useState(null);  // key of active slot
  const [phase,       setPhase]       = useState("");
  const [elapsed,     setElapsed]     = useState(0);   // seconds since pipeline start
  const [errorMsg,    setErrorMsg]    = useState("");
  const timerRef = useRef(null);

  /* ── Timer helpers ────────────────────────────────────── */
  const startTimer = () => {
    setElapsed(0);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000);
  };
  const stopTimer = () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } };
  useEffect(() => () => stopTimer(), []);

  const fmtElapsed = (s) => {
    const m = Math.floor(s / 60), sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

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
    fd.append("due_diligence_notes", entityDetails.ddNotes || "");
    fd.append("cin", entityDetails.cin || "");
    fd.append("pan", entityDetails.pan || "");
    fd.append("sector", entityDetails.sector || "");
    fd.append("turnover", entityDetails.turnover || "");
    fd.append("loan_type", loanDetails.loanType || "");
    fd.append("loan_amount_cr", loanDetails.amountCr || "");
    fd.append("loan_tenure_years", loanDetails.tenureYears || "");
    fd.append("loan_interest_rate", loanDetails.interestRate || "");
    try {
      const res = await API.post("/upload", fd);
      setJobId(res.data.job_id);
      setClassifications(res.data.classifications || []);
      setStatus("idle");
      setPage("classify");
    } catch (e) { setErrorMsg(e?.message || "Upload failed"); setStatus("error"); setPage("app"); }
  };

  const handleApproveClassification = async (approved) => {
    setPage("app");
    setStatus("running");
    startTimer();
    try {
      await API.post(`/pipeline/${jobId}/start`, { classifications: approved });
      pollStatus(jobId);
    } catch (e) { setErrorMsg(e?.message || "Pipeline start failed"); setStatus("error"); }
  };

  const pollStatus = (jid) => {
    const iv = setInterval(async () => {
      try {
        const res = await API.get(`/status/${jid}`);
        setProgress(res.data.progress || 0);
        setPhase(res.data.phase || "");
        if (res.data.status === "done") {
          clearInterval(iv); setStatus("done"); stopTimer();
          const ar = await API.get(`/analysis/${jid}`);
          setAnalysis(ar.data);
        } else if (res.data.status === "error") {
          clearInterval(iv); stopTimer();
          setErrorMsg(res.data.error || "An unexpected error occurred in the pipeline");
          setStatus("error");
        }
      } catch { clearInterval(iv); setStatus("error"); }
    }, 1500);
  };

  /* ── Status dot ───────────────────────────────────────── */
  const statusColor = {done:"#10B981", running:"#F59E0B", error:"#EF4444", idle:"#475569", uploading:"#F59E0B"};

  if (page === "home") {
    return <HomePage onAnalyze={() => setPage("upload")} theme={theme} setTheme={setTheme} />;
  }

  if (page === "upload") {
    return (
      <UploadPage
        onGoHome={() => setPage("home")}
        onSubmit={handleUpload}
        companyName={companyName}
        setCompanyName={setCompanyName}
        docFiles={docFiles}
        addFiles={addFiles}
        removeFile={removeFile}
        dragOver={dragOver}
        setDragOver={setDragOver}
        theme={theme}
        setTheme={setTheme}
        entityDetails={entityDetails}
        setEntityDetails={setEntityDetails}
        loanDetails={loanDetails}
        setLoanDetails={setLoanDetails}
      />
    );
  }

  if (page === "classify") {
    return (
      <ClassificationReview
        classifications={classifications}
        onApprove={handleApproveClassification}
        onBack={() => setPage("upload")}
        theme={theme}
        companyName={companyName}
      />
    );
  }

  return (
    <div style={{ minHeight:"100vh", background: theme === "dark" ? "var(--bg-deep)" : "#fdf8f2", position:"relative", overflow:"hidden" }}>

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
          background:"radial-gradient(circle,rgba(236,91,19,.08) 0%,transparent 70%)",
          animation:"float 30s ease-in-out infinite"}} />
        <div style={{position:"absolute",right:"15%",bottom:"20%",width:400,height:400,borderRadius:"50%",
          background:"radial-gradient(circle,rgba(54,204,235,.07) 0%,transparent 70%)",
          animation:"float 25s ease-in-out 5s infinite"}} />
      </div>

      {/* ── Universal Navbar (matches Home / Upload pages) ── */}
      {(() => {
        const isDark = theme === "dark";
        const navBg     = isDark ? "rgba(34,22,16,0.92)"     : "rgba(253,248,242,0.97)";
        const navBorder = isDark ? "rgba(236,91,19,0.15)"    : "rgba(236,91,19,0.22)";
        const linkColor = isDark ? "#cbd5e1"                 : "#475569";
        const mutedColor= isDark ? "#94a3b8"                 : "#64748b";
        const toggleBg  = isDark ? "rgba(255,255,255,0.07)"  : "rgba(236,91,19,0.1)";
        const toggleBd  = isDark ? "rgba(255,255,255,0.15)"  : "rgba(236,91,19,0.3)";
        const toggleClr = isDark ? "#f1f5f9"                 : "#ec5b13";
        return (
          <header style={{
            position:"sticky", top:0, zIndex:50, width:"100%",
            background: navBg,
            backdropFilter:"blur(14px)", WebkitBackdropFilter:"blur(14px)",
            borderBottom:`1px solid ${navBorder}`,
            padding:"13px 48px",
            fontFamily:"'Public Sans', sans-serif",
          }}>
            <div style={{
              maxWidth:1400, margin:"0 auto",
              display:"flex", alignItems:"center", justifyContent:"space-between", gap:16,
            }}>
              {/* ── Left: Logo + nav links ── */}
              <div style={{ display:"flex", alignItems:"center", gap:36 }}>
                {/* Logo */}
                <div style={{ display:"flex", alignItems:"center", gap:10, cursor:"pointer" }}
                  onClick={() => setPage("home")}>
                  <MSIcon n="account_balance_wallet" style={{ color:"#ec5b13", fontSize:26 }} />
                  <span style={{ fontSize:19, fontWeight:800, letterSpacing:"-0.3px",
                    color: isDark ? "#f1f5f9" : "#1a0e06" }}>
                    Intelli-Credit
                  </span>
                </div>
                {/* Nav links */}
                <nav style={{ display:"flex", gap:28, alignItems:"center" }}>
                  {/* Home */}
                  <button onClick={() => setPage("home")} style={{
                    background:"none", border:"none", cursor:"pointer", padding:"2px 0",
                    fontSize:14, fontWeight:600, color:linkColor,
                    fontFamily:"'Public Sans',sans-serif",
                    transition:"color .15s",
                  }}
                    onMouseOver={e => e.currentTarget.style.color="#ec5b13"}
                    onMouseOut={e => e.currentTarget.style.color=linkColor}
                  >Home</button>
                  {/* Analyze — goes to upload */}
                  <button onClick={() => setPage("upload")} style={{
                    background:"none", border:"none", cursor:"pointer", padding:"2px 0",
                    fontSize:14, fontWeight:600, color:linkColor,
                    fontFamily:"'Public Sans',sans-serif",
                    transition:"color .15s",
                  }}
                    onMouseOver={e => e.currentTarget.style.color="#ec5b13"}
                    onMouseOut={e => e.currentTarget.style.color=linkColor}
                  >Analyze</button>
                  {/* Current results page indicator */}
                  {status === "done" && (
                    <span style={{
                      fontSize:14, fontWeight:700, color:"#ec5b13",
                      borderBottom:"2px solid #ec5b13", paddingBottom:2,
                    }}>Results</span>
                  )}
                </nav>
              </div>

              {/* ── Right: status indicators + LLM + theme toggle ── */}
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                {/* LLM selector */}
                <LLMSelector />

                {/* Timer/status badge */}
                {(status === "running" || status === "uploading" || status === "done") && (
                  <div style={{
                    display:"flex", alignItems:"center", gap:6,
                    padding:"5px 12px", borderRadius:20,
                    background: status === "done" ? "rgba(16,185,129,.12)" : "rgba(236,91,19,.12)",
                    border:`1px solid ${status==="done" ? "rgba(16,185,129,.3)" : "rgba(236,91,19,.3)"}`,
                  }}>
                    <span style={{fontSize:13}}>{status==="done" ? "✅" : "⏱"}</span>
                    <span style={{fontSize:11, fontWeight:700, color: status==="done" ? "#10B981" : "#ec5b13"}}>
                      {status === "done"
                        ? `Done in ${fmtElapsed(elapsed)}`
                        : `Running · ${fmtElapsed(elapsed)}`}
                    </span>
                  </div>
                )}

                {/* Pipeline status dot */}
                <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                  <div style={{
                    width:8, height:8, borderRadius:"50%",
                    background: statusColor[status] || "#475569",
                    animation: status==="running" ? "pulse-dot 1.5s ease-in-out infinite" : "none",
                    boxShadow: status==="running" ? "0 0 8px #F59E0B" : status==="done" ? "0 0 8px #10B981" : "none",
                  }} />
                  <span style={{ fontSize:11, color:mutedColor, textTransform:"capitalize",
                    fontFamily:"'Public Sans',sans-serif" }}>{status}</span>
                </div>

                {/* ── Theme toggle ── */}
                <button
                  onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
                  style={{
                    display:"flex", alignItems:"center", gap:6,
                    background: toggleBg,
                    border:`1px solid ${toggleBd}`,
                    borderRadius:20, padding:"6px 16px", cursor:"pointer",
                    color: toggleClr,
                    fontSize:12, fontWeight:700,
                    fontFamily:"'Public Sans',sans-serif",
                    transition:"all .2s",
                  }}
                  title={isDark ? "Switch to Light mode" : "Switch to Dark mode"}
                >
                  <MSIcon n={isDark ? "light_mode" : "dark_mode"} style={{ fontSize:16 }} />
                  {isDark ? "Light" : "Dark"}
                </button>
              </div>
            </div>
          </header>
        );
      })()}

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
            <div style={{fontSize:13,color:"#94a3b8",marginBottom:8}}>
              {currentStep?.icon} {currentStep?.label || "Initialising…"} &nbsp;·&nbsp; {progress}% complete
            </div>
            <div style={{
              display:"inline-flex",alignItems:"center",gap:8,
              padding:"6px 16px",borderRadius:20,
              background:"rgba(236,91,19,.12)",border:"1px solid rgba(236,91,19,.28)",
            }}>
              <span style={{fontSize:14}}>⏱</span>
              <span style={{fontSize:12,fontWeight:700,color:"#ec5b13"}}>
                Time elapsed: {fmtElapsed(elapsed)}
              </span>
            </div>
          </div>

          {/* ── Pipeline Flow Diagram ─────────────────────── */}
          {(() => {
            /* Distinct color per step */
            const STEP_COLORS = [
              "#0891b2", /* Parsing Documents   — cyan-blue  */
              "#7C3AED", /* OCR & Segmentation  — purple     */
              "#0f766e", /* Table Extraction    — teal       */
              "#059669", /* Cross-Verification  — emerald    */
              "#DC2626", /* Fraud Detection     — red        */
              "#4f46e5", /* Research & Web Intel— indigo     */
              "#D97706", /* Feature Engineering — amber      */
              "#ec5b13", /* ML Credit Scoring   — orange     */
              "#0891b2", /* Explainability(SHAP)— cyan       */
              "#10B981", /* Generating CAM      — green      */
            ];
            return (
              <div style={{width:"100%",maxWidth:900,marginBottom:32}}>
                {[PIPELINE_STEPS.slice(0,5), PIPELINE_STEPS.slice(5,10)].map((row, ri) => (
                  <div key={ri} style={{marginBottom: ri===0 ? 8 : 0}}>
                    <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:0}}>
                      {row.map((s, i) => {
                        const globalIdx = ri*5 + i;
                        const stepColor = STEP_COLORS[globalIdx];
                        const done   = progress >= s.threshold;
                        const active = !done && progress >= (PIPELINE_STEPS[globalIdx-1]?.threshold||0);
                        const bg     = done   ? `linear-gradient(135deg,${stepColor},${stepColor}cc)`
                                     : active ? `linear-gradient(135deg,${stepColor}dd,${stepColor}99)`
                                     : "rgba(34,22,16,0.6)";
                        const shadow = done   ? `0 4px 16px ${stepColor}66`
                                     : active ? `0 4px 20px ${stepColor}88`
                                     : "0 2px 8px rgba(0,0,0,.25)";
                        const borderColor = done ? stepColor : active ? stepColor : "rgba(255,255,255,0.1)";
                        const labelColor  = done ? stepColor : active ? stepColor : "#64748b";
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
                                border: `2px solid ${borderColor}`,
                                animation: active ? "glow-green 1.5s ease-in-out infinite" : "none",
                                transition:"all .4s ease",
                                position:"relative",
                              }}>
                                {done ? "✓" : s.icon}
                                {active && (
                                  <div style={{
                                    position:"absolute",inset:-4,borderRadius:"50%",
                                    border:`2px solid ${stepColor}`,opacity:.6,
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
                              {done   && <div style={{fontSize:8,color:stepColor,marginTop:2,fontWeight:700}}>DONE ✓</div>}
                              {active && <div style={{fontSize:8,color:stepColor,marginTop:2,fontWeight:700,animation:"pulse-dot 1.2s ease infinite"}}>RUNNING…</div>}
                            </div>
                            {/* Arrow between steps */}
                            {i < row.length-1 && (
                              <div style={{
                                flex:0,width:24,height:2,
                                background: progress >= row[i+1]?.threshold ? STEP_COLORS[globalIdx]
                                          : progress >= s.threshold ? STEP_COLORS[globalIdx]+"99" : "rgba(255,255,255,0.1)",
                                position:"relative",marginBottom:28,transition:"background .6s ease",
                              }}>
                                <div style={{
                                  position:"absolute",right:-4,top:"50%",transform:"translateY(-50%)",
                                  width:0,height:0,
                                  borderLeft:`6px solid ${progress >= s.threshold ? STEP_COLORS[globalIdx] : "rgba(255,255,255,0.1)"}`,
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
                          background: progress >= PIPELINE_STEPS[5].threshold ? STEP_COLORS[5]
                                    : progress >= PIPELINE_STEPS[4].threshold ? STEP_COLORS[4]+"88" : "rgba(255,255,255,0.1)",
                          margin:"0 auto",transition:"background .6s ease",
                        }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            );
          })()}

          {/* ── Progress bar ───────────────────────────────── */}
          <div style={{width:500,maxWidth:"90vw",marginBottom:24}}>
              <div style={{height:8,borderRadius:4,background:"rgba(236,91,19,.15)",overflow:"hidden",marginBottom:6}}>
              <div style={{
                height:"100%",borderRadius:4,
                background:"linear-gradient(90deg,#ec5b13,#f97316)",
                width:`${progress}%`,
                transition:"width .8s ease",
                boxShadow:"0 0 12px rgba(236,91,19,.5)",
              }} />
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"#64748b"}}>
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
              borderTopColor:"#ec5b13",
              animation:"spin-slow 1.2s linear infinite",
            }} />
            <div style={{
              position:"absolute",inset:10,borderRadius:"50%",
              border:"2px solid transparent",
              borderTopColor:"#d4420a",
              animation:"spin-slower 1.8s linear infinite",
            }} />
            <div style={{
              position:"absolute",inset:22,borderRadius:"50%",
              border:"2px solid transparent",
              borderTopColor:"#f97316",
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
          <div style={{fontSize:13,color:"#94a3b8",marginBottom:32,textAlign:"center"}}>
            {currentStep?.icon} {currentStep?.label || "Initialising…"}
          </div>

          {/* Progress bar */}
          <div style={{width:360,maxWidth:"90vw"}}>
            <div style={{
              height:6,borderRadius:3,
              background:"rgba(236,91,19,.12)",
              overflow:"hidden",marginBottom:8,
            }}>
              <div style={{
                height:"100%",borderRadius:3,
                background:"linear-gradient(90deg,#ec5b13,#f97316)",
                width:`${progress}%`,
                transition:"width .6s ease",
                boxShadow:"0 0 12px rgba(236,91,19,.5)",
              }} />
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"#64748b"}}>
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
          {/* Tab bar — theme-aware */}
          {(() => {
            const isDark = theme === "dark";
            return (
              <div data-tabbar style={{
                display:"flex",gap:4,padding:"8px 24px 0",
                position:"sticky",top:54,zIndex:40,
                background: isDark ? "rgba(34,22,16,0.92)" : "rgba(253,248,242,0.97)",
                backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)",
                borderBottom:`1px solid ${isDark ? "rgba(236,91,19,.22)" : "rgba(236,91,19,.2)"}`,
                overflowX:"auto",
              }}>
                {TABS.map(t => (
                  <button key={t.id} onClick={()=>setActiveTab(t.id)} style={{
                    padding:"8px 16px",borderRadius:"10px 10px 0 0",
                    fontSize:12,fontWeight:600,cursor:"pointer",border:"none",
                    whiteSpace:"nowrap",
                    fontFamily:"'Public Sans',sans-serif",
                    background: activeTab===t.id ? "rgba(236,91,19,.12)" : "transparent",
                    color: activeTab===t.id ? "#ec5b13" : isDark ? "#94a3b8" : "#64748b",
                    borderBottom: activeTab===t.id ? "2px solid #ec5b13" : "2px solid transparent",
                    boxShadow: activeTab===t.id ? "0 0 16px rgba(236,91,19,.15)" : "none",
                    transition:"all .25s ease",
                  }}>
                    {t.label}
                  </button>
                ))}
              </div>
            );
          })()}

          <div className="fade-in" style={{padding:24}} key={activeTab}>
            {activeTab==="Dashboard"        && <Dashboard    analysis={analysis} theme={theme} />}
            {activeTab==="Decision"         && <DecisionPanel analysis={analysis} jobId={jobId} theme={theme} />}
            {activeTab==="Fraud Graph"      && <FraudGraph   analysis={analysis} theme={theme} />}
            {activeTab==="Promoter Network" && <PromoterGraph analysis={analysis} theme={theme} />}
            {activeTab==="Agent Reports"    && <AgentReports  analysis={analysis} theme={theme} />}
            {activeTab==="Evidence"         && <EvidenceViewer analysis={analysis} theme={theme} />}
            {activeTab==="CAM"              && <CAMViewer     jobId={jobId} theme={theme} />}
            {activeTab==="Schema"           && <SchemaEditor  theme={theme} />}
          </div>
        </div>
      )}

      {/* ── ERROR ─────────────────────────────────────────── */}
      {status==="error" && (
        <div className="fade-in" style={{
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
          minHeight:"calc(100vh - 62px)", padding:"24px",
        }}>
          <div style={{fontSize:56,marginBottom:16,filter:"drop-shadow(0 0 20px rgba(239,68,68,.5))"}}>❌</div>
          <p style={{color:"#F87171",fontSize:16,fontWeight:600,marginBottom:8}}>Processing failed</p>
          {errorMsg && (
            <div style={{
              maxWidth:600,background:"rgba(239,68,68,.08)",border:"1px solid rgba(239,68,68,.25)",
              borderRadius:10,padding:"10px 16px",marginBottom:16,
            }}>
              <p style={{color:"#fca5a5",fontSize:12,fontFamily:"monospace",margin:0,wordBreak:"break-word",lineHeight:1.5}}>
                {errorMsg}
              </p>
            </div>
          )}
          <button onClick={()=>{setStatus("idle");setDocFiles(emptySlots());setProgress(0);setErrorMsg("");setClassifications([]);setPage("upload");}} style={{
            padding:"10px 24px",borderRadius:10,fontSize:13,fontWeight:600,
            color:"white",background:"rgba(239,68,68,.2)",border:"1px solid rgba(239,68,68,.4)",cursor:"pointer",
          }}>↩ Try Again</button>
        </div>
      )}
    </div>
  );
}

