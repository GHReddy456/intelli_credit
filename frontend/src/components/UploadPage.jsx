import React, { useEffect, useState } from "react";

/* ── Font + Material Symbols loader ──────────────────── */
function useFonts() {
  useEffect(() => {
    if (document.getElementById("up-fonts")) return;
    const lk1 = document.createElement("link");
    lk1.id = "up-fonts"; lk1.rel = "stylesheet";
    lk1.href = "https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;800;900&display=swap";
    document.head.appendChild(lk1);
    const lk2 = document.createElement("link");
    lk2.rel = "stylesheet";
    lk2.href = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200";
    document.head.appendChild(lk2);
  }, []);
}

function Icon({ n, style = {} }) {
  return <span className="material-symbols-outlined" style={{ userSelect:"none", ...style }}>{n}</span>;
}

/* ── Doc type metadata (5 challenge + 4 additional) ───── */
const SLOT_META = {
  annual_report:        { icon: "analytics",       color: "#a855f7", bg: "rgba(168,85,247,0.2)",  label: "Annual Report",         sub: "FY 2022–24 · PDF",             group: "challenge" },
  alm:                  { icon: "account_balance",  color: "#0891b2", bg: "rgba(8,145,178,0.2)",   label: "ALM Statement",         sub: "Asset-Liability Maturity",      group: "challenge" },
  shareholding_pattern: { icon: "pie_chart",        color: "#059669", bg: "rgba(5,150,105,0.2)",   label: "Shareholding Pattern",  sub: "Promoter / Public / FII",       group: "challenge" },
  borrowing_profile:    { icon: "request_quote",    color: "#D97706", bg: "rgba(217,119,6,0.2)",   label: "Borrowing Profile",     sub: "Debt structure & covenants",    group: "challenge" },
  portfolio_performance:{ icon: "trending_up",      color: "#7C3AED", bg: "rgba(124,58,237,0.2)",  label: "Portfolio Performance",  sub: "Portfolio cuts & returns",       group: "challenge" },
  gstr3b:               { icon: "receipt_long",     color: "#60a5fa", bg: "rgba(59,130,246,0.2)",  label: "GSTR-3B",               sub: "Last 12 months returns",        group: "additional" },
  bank_statement:       { icon: "savings",          color: "#4ade80", bg: "rgba(34,197,94,0.2)",   label: "Bank Statement",        sub: "6–12 months PDF",               group: "additional" },
  itr6:                 { icon: "description",      color: "#fb923c", bg: "rgba(249,115,22,0.2)",  label: "ITR-6",                 sub: "Last 3 assessment years",       group: "additional" },
  legal_docs:           { icon: "gavel",            color: "#f87171", bg: "rgba(239,68,68,0.2)",   label: "Legal Docs",            sub: "MOA · AOA · Charges",           group: "additional" },
};

const SECTORS = [
  "Steel", "Textile", "Real Estate", "IT / Software", "Pharma / Healthcare",
  "NBFC / Financial Services", "Infrastructure", "Agriculture", "Automobile",
  "Cement", "FMCG", "Energy", "Mining", "Chemicals", "Telecom", "Logistics", "Other",
];

const LOAN_TYPES = [
  "Working Capital", "Term Loan", "Both (WC + TL)", "Project Finance",
  "Letter of Credit", "Bank Guarantee", "Other",
];

const STEPS = [
  { num: 1, label: "Entity Details", icon: "business",        desc: "Company identification & profile" },
  { num: 2, label: "Loan Details",   icon: "account_balance", desc: "Facility requirements & terms" },
  { num: 3, label: "Upload Docs",    icon: "upload_file",     desc: "Submit documents for AI analysis" },
];

export default function UploadPage({
  onGoHome,
  onSubmit,
  companyName,
  setCompanyName,
  docFiles,
  addFiles,
  removeFile,
  dragOver,
  setDragOver,
  theme = "dark",
  setTheme,
  entityDetails = {},
  setEntityDetails = () => {},
  loanDetails = {},
  setLoanDetails = () => {},
}) {
  useFonts();
  const [step, setStep] = useState(1);
  const isDark = theme === "dark";

  const T = {
    bg:        isDark ? "linear-gradient(100deg, #0a0604 0%, #110c07 35%, #1a0f08 55%, #2a1206 75%, #1a0d05 100%)" : "#fdf8f2",
    color:     isDark ? "#f1f5f9" : "#1a0e06",
    muted:     isDark ? "#94a3b8" : "#64748b",
    navBorder: isDark ? "rgba(236,91,19,0.15)" : "rgba(236,91,19,0.2)",
    linkColor: isDark ? "#cbd5e1" : "#475569",
    inputBg:   isDark ? "rgba(34,22,16,0.6)" : "#ffffff",
    inputBd:   isDark ? "rgba(236,91,19,0.25)" : "rgba(236,91,19,0.35)",
    cardBg:    isDark ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.85)",
    cardBd:    isDark ? "rgba(255,255,255,0.1)" : "rgba(236,91,19,0.18)",
    cardTopBd: isDark ? "rgba(255,255,255,0.06)" : "rgba(236,91,19,0.1)",
    footerBd:  isDark ? "rgba(255,255,255,0.07)" : "rgba(236,91,19,0.12)",
  };
  const glass = isDark
    ? { background:"rgba(34,22,16,0.7)", backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.2)" }
    : { background:"rgba(255,255,255,0.88)", backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.22)" };

  const DOC_KEYS = Object.keys(SLOT_META);
  const CHALLENGE_KEYS = DOC_KEYS.filter(k => SLOT_META[k].group === "challenge");
  const EXTRA_KEYS = DOC_KEYS.filter(k => SLOT_META[k].group === "additional");
  const totalFiles = Object.values(docFiles).flat().length;
  const filledSlots = DOC_KEYS.filter(k => docFiles[k]?.length > 0).length;

  /* ── Input helper ──────────────────────────────────── */
  const inputStyle = {
    width:"100%", padding:"13px 16px", borderRadius:10,
    border:`1px solid ${T.inputBd}`, background:T.inputBg, color:T.color,
    fontSize:14, fontFamily:"'Public Sans',sans-serif", outline:"none",
    boxSizing:"border-box", transition:"border-color .2s, box-shadow .2s",
  };
  const labelStyle = {
    display:"block", fontSize:11, fontWeight:700, color:T.muted,
    letterSpacing:"0.12em", marginBottom:8, textTransform:"uppercase",
  };
  const focusHandler = (e) => {
    e.target.style.borderColor = "rgba(236,91,19,0.7)";
    e.target.style.boxShadow = isDark ? "inset 0 0 15px rgba(236,91,19,0.08)" : "0 0 0 3px rgba(236,91,19,0.12)";
  };
  const blurHandler = (e) => {
    e.target.style.borderColor = T.inputBd;
    e.target.style.boxShadow = "none";
  };

  const updateEntity = (key, val) => setEntityDetails(prev => ({ ...prev, [key]: val }));
  const updateLoan = (key, val) => setLoanDetails(prev => ({ ...prev, [key]: val }));

  /* ── Doc card renderer ─────────────────────────────── */
  const renderDocCard = (key, si) => {
    const meta = SLOT_META[key];
    const slotFiles = docFiles[key] || [];
    const hasFiles = slotFiles.length > 0;
    const isOver = dragOver === key;
    return (
      <div key={key}
        style={{
          ...glass, borderRadius:18, overflow:"hidden",
          border:`1px solid ${isOver ? meta.color : hasFiles ? meta.color+"60" : T.cardBd}`,
          background: isOver ? meta.bg : T.cardBg,
          transition:"all .25s ease",
          animation:`fadeSlideIn .4s ease ${si * 0.06}s both`,
        }}
        onDrop={e => { e.preventDefault(); setDragOver(null); addFiles(key, e.dataTransfer.files); }}
        onDragOver={e => { e.preventDefault(); setDragOver(key); }}
        onDragLeave={() => setDragOver(null)}
      >
        <div style={{ padding:"24px 18px 18px", textAlign:"center", borderBottom:`1px solid ${hasFiles ? meta.color+"30" : T.cardTopBd}` }}>
          <div style={{
            width:56, height:56, borderRadius:14, background:meta.bg,
            display:"flex", alignItems:"center", justifyContent:"center",
            margin:"0 auto 12px",
          }}>
            <Icon n={meta.icon} style={{ color:meta.color, fontSize:26 }} />
          </div>
          <div style={{ fontSize:13, fontWeight:700, color:T.color, marginBottom:3 }}>{meta.label}</div>
          <div style={{ fontSize:11, color:T.muted }}>{meta.sub}</div>
          {hasFiles && (
            <div style={{
              display:"inline-block", marginTop:7,
              background:meta.bg, color:meta.color,
              borderRadius:20, padding:"2px 12px", fontSize:10, fontWeight:700,
            }}>{slotFiles.length} file{slotFiles.length > 1 ? "s" : ""} ✓</div>
          )}
        </div>
        <div style={{ padding:"14px 18px" }}>
          {slotFiles.length === 0 ? (
            <div style={{ textAlign:"center" }}>
              <p style={{ fontSize:10, color:"#64748b", marginBottom:10, lineHeight:1.5 }}>
                {isOver ? "Drop here!" : "Drag & drop or click"}
              </p>
              <input type="file" multiple accept=".pdf,.xlsx,.xml,.doc,.docx,.csv" id={`up-${key}`} style={{ display:"none" }}
                onChange={e => addFiles(key, e.target.files)} />
              <label htmlFor={`up-${key}`} style={{
                display:"inline-block", padding:"8px 22px", borderRadius:10, cursor:"pointer",
                fontSize:11, fontWeight:700, border:`1.5px solid ${meta.color}`,
                color:meta.color, background:"transparent", transition:"background .2s, color .2s",
              }}
                onMouseOver={e => { e.currentTarget.style.background = meta.color; e.currentTarget.style.color = "#fff"; }}
                onMouseOut={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = meta.color; }}
              >UPLOAD</label>
            </div>
          ) : (
            <div>
              {slotFiles.map((f, fi) => (
                <div key={fi} style={{
                  display:"flex", alignItems:"center", gap:6,
                  padding:"5px 8px", borderRadius:7, marginBottom:4,
                  background:isDark ? "rgba(255,255,255,0.04)" : "rgba(236,91,19,0.04)",
                  border:`1px solid ${isDark ? "rgba(255,255,255,0.07)" : "rgba(236,91,19,0.12)"}`,
                }}>
                  <Icon n="picture_as_pdf" style={{ color:meta.color, fontSize:13 }} />
                  <span style={{ fontSize:10, color:T.color, flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f.name}</span>
                  <button onClick={() => removeFile(key, fi)} style={{
                    background:"none", border:"none", cursor:"pointer", color:"#64748b", fontSize:14, lineHeight:1, padding:0,
                  }}>×</button>
                </div>
              ))}
              <input type="file" multiple accept=".pdf,.xlsx,.xml,.doc,.docx,.csv" id={`up-${key}-m`} style={{ display:"none" }}
                onChange={e => addFiles(key, e.target.files)} />
              <label htmlFor={`up-${key}-m`} style={{
                display:"block", textAlign:"center", marginTop:5, padding:"4px", borderRadius:7, cursor:"pointer",
                fontSize:10, fontWeight:600, color:meta.color, border:`1px dashed ${meta.color}60`,
              }}>+ Add more</label>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ minHeight:"100vh", background:T.bg, fontFamily:"'Public Sans', sans-serif", color:T.color, display:"flex", flexDirection:"column" }}>

      {/* ── Ambient orbs ───────────────────────────────── */}
      <div style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:0, overflow:"hidden" }}>
        <div style={{ position:"absolute", inset:0, background:"linear-gradient(95deg, rgba(236,91,19,0.08) 0%, rgba(0,198,255,0.06) 18%, transparent 40%, transparent 60%, rgba(0,198,255,0.07) 82%, rgba(236,91,19,0.08) 100%)" }} />
        <div style={{ position:"absolute", top:"15%", left:"-6%", width:isDark?680:500, height:isDark?680:500, borderRadius:"50%", background:isDark?"radial-gradient(circle,rgba(236,91,19,0.28) 0%,rgba(236,91,19,0.1) 40%,transparent 70%)":"radial-gradient(circle,rgba(236,91,19,0.18) 0%,rgba(236,91,19,0.06) 40%,transparent 70%)" }} />
        <div style={{ position:"absolute", bottom:"0%", right:"8%", width:isDark?520:400, height:isDark?520:400, borderRadius:"50%", background:isDark?"radial-gradient(circle,rgba(0,198,255,0.20) 0%,rgba(0,198,255,0.07) 45%,transparent 70%)":"radial-gradient(circle,rgba(0,198,255,0.10) 0%,rgba(0,198,255,0.03) 45%,transparent 70%)" }} />
        <div style={{ position:"absolute", top:"15%", right:"-6%", width:isDark?680:500, height:isDark?680:500, borderRadius:"50%", background:isDark?"radial-gradient(circle,rgba(236,91,19,0.28) 0%,rgba(236,91,19,0.1) 40%,transparent 70%)":"radial-gradient(circle,rgba(236,91,19,0.18) 0%,rgba(236,91,19,0.06) 40%,transparent 70%)" }} />
      </div>

      {/* ── Nav ────────────────────────────────────────── */}
      <header style={{ position:"sticky", top:0, zIndex:50, ...glass, borderBottom:`1px solid ${T.navBorder}`, padding:"14px 80px" }}>
        <div style={{ maxWidth:1280, margin:"0 auto", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div style={{ display:"flex", alignItems:"center", gap:40 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <Icon n="diamond" style={{ color:"#ec5b13", fontSize:28 }} />
              <span style={{ fontSize:20, fontWeight:800, letterSpacing:"-0.3px" }}>Intelli-Credit</span>
            </div>
            <nav style={{ display:"flex", gap:32 }}>
              <a href="#" onClick={e => { e.preventDefault(); onGoHome(); }} style={{ color:T.linkColor, fontSize:14, fontWeight:600, textDecoration:"none", paddingBottom:3 }}
                onMouseOver={e => e.currentTarget.style.color="#ec5b13"} onMouseOut={e => e.currentTarget.style.color=T.linkColor}>Home</a>
              <a href="#" onClick={e => e.preventDefault()} style={{ color:"#ec5b13", fontSize:14, fontWeight:700, textDecoration:"none", borderBottom:"2px solid #ec5b13", paddingBottom:3 }}>Analyze</a>
            </nav>
          </div>
          <button onClick={() => setTheme && setTheme(isDark ? "light" : "dark")} style={{
            display:"flex", alignItems:"center", gap:6,
            background: isDark ? "rgba(255,255,255,0.07)" : "rgba(236,91,19,0.1)",
            border:`1px solid ${isDark ? "rgba(255,255,255,0.15)" : "rgba(236,91,19,0.3)"}`,
            borderRadius:20, padding:"6px 16px", cursor:"pointer",
            color: isDark ? "#f1f5f9" : "#ec5b13", fontSize:12, fontWeight:700,
            fontFamily:"'Public Sans',sans-serif",
          }}>
            <Icon n={isDark ? "light_mode" : "dark_mode"} style={{ fontSize:16 }} />
            {isDark ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <main style={{ flex:1, position:"relative", zIndex:1 }}>

        {/* ── Step indicator ────────────────────────────── */}
        <section style={{ padding:"40px 80px 8px", maxWidth:1280, margin:"0 auto" }}>
          <div style={{ display:"flex", justifyContent:"center", alignItems:"center", gap:0, marginBottom:12 }}>
            {STEPS.map((s, i) => {
              const active = step === s.num;
              const done = step > s.num;
              const circColor = done ? "#10B981" : active ? "#ec5b13" : (isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)");
              const textColor = active ? "#ec5b13" : done ? "#10B981" : T.muted;
              return (
                <React.Fragment key={s.num}>
                  <div style={{ display:"flex", flexDirection:"column", alignItems:"center", cursor:"pointer", minWidth:140 }} onClick={() => setStep(s.num)}>
                    <div style={{
                      width:44, height:44, borderRadius:"50%",
                      background: done ? "rgba(16,185,129,0.15)" : active ? "rgba(236,91,19,0.15)" : "transparent",
                      border:`2px solid ${circColor}`,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      marginBottom:8, transition:"all .3s",
                    }}>
                      {done
                        ? <Icon n="check" style={{ color:"#10B981", fontSize:22 }} />
                        : <Icon n={s.icon} style={{ color: active ? "#ec5b13" : T.muted, fontSize:22 }} />
                      }
                    </div>
                    <div style={{ fontSize:12, fontWeight:active ? 800 : 600, color:textColor, textAlign:"center" }}>{s.label}</div>
                    <div style={{ fontSize:10, color:T.muted, textAlign:"center", marginTop:2 }}>{s.desc}</div>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{
                      flex:"0 0 80px", height:2, marginBottom:36,
                      background: step > s.num ? "#10B981" : (isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)"),
                      transition:"background .3s",
                    }} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </section>

        {/* ── Hero ──────────────────────────────────────── */}
        <section style={{ padding:"16px 80px 28px", maxWidth:1280, margin:"0 auto", textAlign:"center" }}>
          <div style={{ marginBottom:14 }}>
            <span style={{
              display:"inline-flex", alignItems:"center", gap:6,
              background:"rgba(236,91,19,0.15)", border:"1px solid rgba(236,91,19,0.4)",
              borderRadius:20, padding:"6px 16px", fontSize:11, fontWeight:800, color:"#ec5b13", letterSpacing:"0.1em",
            }}>
              <Icon n="shield" style={{ fontSize:14 }} />
              STEP {step} OF 3
            </span>
          </div>
          <h1 style={{ fontSize:44, fontWeight:900, letterSpacing:"-1.5px", lineHeight:1.1, margin:"0 0 12px" }}>
            {STEPS[step - 1].label}
          </h1>
          <p style={{ fontSize:15, color:T.muted, maxWidth:550, margin:"0 auto", lineHeight:1.7 }}>
            {step === 1 && "Enter the company identification details and business profile for credit assessment."}
            {step === 2 && "Specify the loan facility requirements, amount, tenure, and preferred terms."}
            {step === 3 && "Upload corporate documents for AI-powered extraction and analysis."}
          </p>
        </section>

        {/* ══════════ STEP 1: Entity Details ═══════════ */}
        {step === 1 && (
          <section style={{ maxWidth:720, margin:"0 auto 36px", padding:"0 24px" }}>
            <div style={{ ...glass, borderRadius:20, padding:"32px 36px" }}>
              {/* Company Name */}
              <div style={{ marginBottom:20 }}>
                <label style={labelStyle}>Company Entity Name *</label>
                <input type="text" placeholder="e.g. Trident Components Pvt. Ltd."
                  value={companyName} onChange={e => setCompanyName(e.target.value)}
                  style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
              </div>
              {/* CIN + PAN row */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:20 }}>
                <div>
                  <label style={labelStyle}>CIN (Corporate ID Number)</label>
                  <input type="text" placeholder="e.g. U29100MH2015PTC123456"
                    value={entityDetails.cin || ""} onChange={e => updateEntity("cin", e.target.value)}
                    style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
                </div>
                <div>
                  <label style={labelStyle}>PAN</label>
                  <input type="text" placeholder="e.g. AABCT1234E" maxLength={10}
                    value={entityDetails.pan || ""} onChange={e => updateEntity("pan", e.target.value.toUpperCase())}
                    style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
                </div>
              </div>
              {/* Sector + Turnover row */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:20 }}>
                <div>
                  <label style={labelStyle}>Industry Sector *</label>
                  <select value={entityDetails.sector || ""} onChange={e => updateEntity("sector", e.target.value)}
                    style={{ ...inputStyle, cursor:"pointer" }} onFocus={focusHandler} onBlur={blurHandler}>
                    <option value="">Select sector…</option>
                    {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Annual Turnover (₹ Crores)</label>
                  <input type="number" placeholder="e.g. 150" min={0}
                    value={entityDetails.turnover || ""} onChange={e => updateEntity("turnover", e.target.value)}
                    style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
                </div>
              </div>
              {/* Due Diligence Notes */}
              <div style={{ marginBottom:24 }}>
                <label style={labelStyle}>Due Diligence Notes (Optional)</label>
                <textarea placeholder="Any additional context, site-visit observations, known risks…"
                  value={entityDetails.ddNotes || ""} onChange={e => updateEntity("ddNotes", e.target.value)}
                  rows={3}
                  style={{ ...inputStyle, resize:"vertical", minHeight:70 }} onFocus={focusHandler} onBlur={blurHandler} />
              </div>
              {/* Security badge */}
              <div style={{ display:"inline-flex", alignItems:"center", gap:10, background:"rgba(0,198,255,0.07)", border:"1px solid rgba(0,198,255,0.25)", borderRadius:12, padding:"10px 16px", marginBottom:24 }}>
                <Icon n="shield" style={{ color:"#00c6ff", fontSize:22 }} />
                <div>
                  <div style={{ fontSize:11, fontWeight:700, color:isDark ? "#cbd5e1" : "#64748b", letterSpacing:"0.05em" }}>Security Level</div>
                  <div style={{ fontSize:12, color:"#00c6ff", fontWeight:600 }}>AES-256 Bit Encrypted</div>
                </div>
              </div>
              {/* Next button */}
              <button onClick={() => setStep(2)} disabled={!companyName.trim()} style={{
                width:"100%", padding:"15px", borderRadius:14, fontWeight:800, fontSize:14,
                cursor: companyName.trim() ? "pointer" : "not-allowed",
                border:"none", fontFamily:"'Public Sans',sans-serif", letterSpacing:"0.3px",
                color: companyName.trim() ? "white" : T.muted,
                background: companyName.trim() ? "linear-gradient(135deg, #ec5b13 0%, #d4420a 100%)" : (isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"),
                boxShadow: companyName.trim() ? "0 4px 20px rgba(236,91,19,0.4)" : "none",
                display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                transition:"all .2s",
              }}>
                Next: Loan Details <Icon n="arrow_forward" style={{ fontSize:18 }} />
              </button>
            </div>
          </section>
        )}

        {/* ══════════ STEP 2: Loan Details ═══════════ */}
        {step === 2 && (
          <section style={{ maxWidth:720, margin:"0 auto 36px", padding:"0 24px" }}>
            <div style={{ ...glass, borderRadius:20, padding:"32px 36px" }}>
              {/* Loan Type */}
              <div style={{ marginBottom:20 }}>
                <label style={labelStyle}>Loan / Facility Type *</label>
                <select value={loanDetails.loanType || ""} onChange={e => updateLoan("loanType", e.target.value)}
                  style={{ ...inputStyle, cursor:"pointer" }} onFocus={focusHandler} onBlur={blurHandler}>
                  <option value="">Select facility type…</option>
                  {LOAN_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              {/* Amount + Tenure row */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:20 }}>
                <div>
                  <label style={labelStyle}>Amount Requested (₹ Crores) *</label>
                  <input type="number" placeholder="e.g. 25" min={0}
                    value={loanDetails.amountCr || ""} onChange={e => updateLoan("amountCr", e.target.value)}
                    style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
                </div>
                <div>
                  <label style={labelStyle}>Preferred Tenure (Years)</label>
                  <input type="number" placeholder="e.g. 5" min={1} max={30}
                    value={loanDetails.tenureYears || ""} onChange={e => updateLoan("tenureYears", e.target.value)}
                    style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
                </div>
              </div>
              {/* Interest Rate */}
              <div style={{ marginBottom:28 }}>
                <label style={labelStyle}>Expected Interest Rate (% p.a.)</label>
                <input type="number" placeholder="e.g. 10.5" min={0} max={30} step={0.1}
                  value={loanDetails.interestRate || ""} onChange={e => updateLoan("interestRate", e.target.value)}
                  style={inputStyle} onFocus={focusHandler} onBlur={blurHandler} />
              </div>
              {/* Summary card */}
              {loanDetails.loanType && loanDetails.amountCr && (
                <div style={{
                  ...glass, borderRadius:14, padding:"16px 20px", marginBottom:24,
                  border:"1px solid rgba(16,185,129,0.3)", background:"rgba(16,185,129,0.05)",
                }}>
                  <div style={{ fontSize:11, fontWeight:700, color:"#10B981", letterSpacing:"0.1em", marginBottom:8 }}>FACILITY SUMMARY</div>
                  <div style={{ fontSize:14, color:T.color, lineHeight:1.8 }}>
                    <strong>{loanDetails.loanType}</strong> facility of <strong>₹{loanDetails.amountCr} Cr</strong>
                    {loanDetails.tenureYears && <> for <strong>{loanDetails.tenureYears} years</strong></>}
                    {loanDetails.interestRate && <> at <strong>{loanDetails.interestRate}% p.a.</strong></>}
                    {" "}for <strong>{companyName || "the entity"}</strong>
                  </div>
                </div>
              )}
              {/* Nav buttons */}
              <div style={{ display:"flex", gap:12 }}>
                <button onClick={() => setStep(1)} style={{
                  padding:"15px 28px", borderRadius:14, fontSize:13, fontWeight:700, cursor:"pointer",
                  background:"transparent", border:`1px solid ${T.cardBd}`, color:T.muted,
                  fontFamily:"'Public Sans',sans-serif", display:"flex", alignItems:"center", gap:6,
                }}>
                  <Icon n="arrow_back" style={{ fontSize:16 }} /> Back
                </button>
                <button onClick={() => setStep(3)} disabled={!loanDetails.loanType || !loanDetails.amountCr} style={{
                  flex:1, padding:"15px", borderRadius:14, fontWeight:800, fontSize:14,
                  cursor: (loanDetails.loanType && loanDetails.amountCr) ? "pointer" : "not-allowed",
                  border:"none", fontFamily:"'Public Sans',sans-serif",
                  color: (loanDetails.loanType && loanDetails.amountCr) ? "white" : T.muted,
                  background: (loanDetails.loanType && loanDetails.amountCr)
                    ? "linear-gradient(135deg, #ec5b13, #d4420a)" : (isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"),
                  boxShadow: (loanDetails.loanType && loanDetails.amountCr) ? "0 4px 20px rgba(236,91,19,0.4)" : "none",
                  display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                }}>
                  Next: Upload Documents <Icon n="arrow_forward" style={{ fontSize:18 }} />
                </button>
              </div>
            </div>
          </section>
        )}

        {/* ══════════ STEP 3: Document Upload ═══════════ */}
        {step === 3 && (
          <>
            {/* Challenge-required documents */}
            <section style={{ maxWidth:1280, margin:"0 auto 12px", padding:"0 24px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16 }}>
                <Icon n="verified" style={{ color:"#ec5b13", fontSize:20 }} />
                <span style={{ fontSize:13, fontWeight:800, color:"#ec5b13", letterSpacing:"0.08em", textTransform:"uppercase" }}>
                  Primary Documents (Required)
                </span>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:16 }}>
                {CHALLENGE_KEYS.map((key, i) => renderDocCard(key, i))}
              </div>
            </section>

            {/* Additional intelligence documents */}
            <section style={{ maxWidth:1280, margin:"24px auto 12px", padding:"0 24px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:16 }}>
                <Icon n="add_circle_outline" style={{ color:T.muted, fontSize:20 }} />
                <span style={{ fontSize:13, fontWeight:800, color:T.muted, letterSpacing:"0.08em", textTransform:"uppercase" }}>
                  Additional Intelligence Documents (Optional)
                </span>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(200px,1fr))", gap:16 }}>
                {EXTRA_KEYS.map((key, i) => renderDocCard(key, i + CHALLENGE_KEYS.length))}
              </div>
            </section>

            {/* Nav + Submit */}
            <section style={{ maxWidth:760, margin:"28px auto 52px", padding:"0 24px" }}>
              {/* File chips */}
              {totalFiles > 0 && (
                <div style={{ display:"flex", gap:6, flexWrap:"wrap", justifyContent:"center", marginBottom:14 }}>
                  {DOC_KEYS.filter(k => docFiles[k]?.length > 0).map(k => {
                    const m = SLOT_META[k];
                    return (
                      <span key={k} style={{
                        fontSize:10, padding:"3px 10px", borderRadius:20,
                        background:m.bg, color:m.color, fontWeight:600, border:`1px solid ${m.color}40`,
                      }}>✓ {m.label} ({docFiles[k].length})</span>
                    );
                  })}
                </div>
              )}
              <div style={{ display:"flex", gap:12 }}>
                <button onClick={() => setStep(2)} style={{
                  padding:"15px 28px", borderRadius:14, fontSize:13, fontWeight:700, cursor:"pointer",
                  background:"transparent", border:`1px solid ${T.cardBd}`, color:T.muted,
                  fontFamily:"'Public Sans',sans-serif", display:"flex", alignItems:"center", gap:6,
                }}>
                  <Icon n="arrow_back" style={{ fontSize:16 }} /> Back
                </button>
                <button onClick={onSubmit} disabled={totalFiles === 0} style={{
                  flex:1, padding:"16px", borderRadius:14, fontWeight:800, fontSize:14,
                  cursor: totalFiles > 0 ? "pointer" : "not-allowed",
                  border:"none", fontFamily:"'Public Sans',sans-serif", letterSpacing:"0.3px",
                  color: totalFiles > 0 ? "white" : T.muted,
                  background: totalFiles > 0 ? "linear-gradient(135deg, #ec5b13, #d4420a)" : (isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"),
                  boxShadow: totalFiles > 0 ? "0 4px 20px rgba(236,91,19,0.4)" : "none",
                  display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                  transition:"all .15s",
                }}>
                  <Icon n="rocket_launch" style={{ fontSize:18 }} />
                  {totalFiles === 0 ? "Upload at least one document" : `Upload & Classify · ${totalFiles} file${totalFiles > 1 ? "s" : ""}`}
                </button>
              </div>
            </section>
          </>
        )}
      </main>

      {/* ── Footer ──────────────────────────────────── */}
      <footer style={{ ...glass, borderTop:`1px solid ${T.footerBd}`, padding:"20px 80px", position:"relative", zIndex:1 }}>
        <div style={{ maxWidth:1280, margin:"0 auto", display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:12 }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <Icon n="security" style={{ color:"#94a3b8", fontSize:18 }} />
            <span style={{ fontSize:12, color:"#64748b" }}>Intelli-Credit Analytics · Secure Enterprise Portal</span>
          </div>
          <span style={{ fontSize:11, color:"#475569" }}>© 2024 Intelli-Credit Edition</span>
        </div>
      </footer>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
