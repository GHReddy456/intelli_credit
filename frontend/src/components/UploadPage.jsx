import React, { useEffect, useRef, useState } from "react";

/* ── Font + Material Symbols loader (shared) ─────────────────────── */
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
  return (
    <span className="material-symbols-outlined" style={{ userSelect:"none", ...style }}>
      {n}
    </span>
  );
}

/* ── Color palette per doc category ───────────────────────────────── */
const SLOT_META = {
  annual_report:  { icon: "analytics",      color: "#a855f7", bg: "rgba(168,85,247,0.2)",  label: "Annual Report",  sub: "FY 2022–24 · PDF" },
  gstr3b:         { icon: "receipt_long",   color: "#60a5fa", bg: "rgba(59,130,246,0.2)",  label: "GSTR-3B",        sub: "Last 12 months returns" },
  bank_statement: { icon: "account_balance",color: "#4ade80", bg: "rgba(34,197,94,0.2)",   label: "Bank Statement", sub: "6–12 months PDF" },
  itr6:           { icon: "description",    color: "#fb923c", bg: "rgba(249,115,22,0.2)",  label: "ITR-6",          sub: "Last 3 assessment years" },
  legal_docs:     { icon: "gavel",          color: "#f87171", bg: "rgba(239,68,68,0.2)",   label: "Legal Docs",     sub: "MOA · AOA · Charges" },
};

/* ── Base styles computed inside component (theme-aware) ──────────── */
// glass is now computed inside the component

const AVATAR = "https://lh3.googleusercontent.com/aida-public/AB6AXuCcvhEGJ1FePvDl4c0ONLJ3Dk3d_2XRSwVWJPaCRPJR5FLdfrb9z4iKv2PvLt14Ry6ACfLJg4rkHkPIUOGHzjn3Y5fq0O4HJqFHLo7UXbcqxc8EAiE00kpLMnT5UJBIakfHW-KImcS-ZyYS2QTHWL6hC7k5dpNcHBb72M8GFmFmPBH4nX2wusnz-dvSsz2OqOeJrgm_BhivQGDT8bqNE8UoIQG5PikqXM11Og8VTSiPiNKSf_JD3k7nYBM3tS5lZ7gRt6bSaZOGqg";

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
}) {
  useFonts();
  const isDark = theme === "dark";
  const T = {
    bg:        isDark
      ? "linear-gradient(100deg, #0a0604 0%, #110c07 35%, #1a0f08 55%, #2a1206 75%, #1a0d05 100%)"
      : "#fdf8f2",
    color:     isDark ? "#f1f5f9"                  : "#1a0e06",
    muted:     isDark ? "#94a3b8"                  : "#64748b",
    subtle:    isDark ? "#64748b"                  : "#94a3b8",
    navBorder: isDark ? "rgba(236,91,19,0.15)"     : "rgba(236,91,19,0.2)",
    linkColor: isDark ? "#cbd5e1"                  : "#475569",
    inputBg:   isDark ? "rgba(34,22,16,0.6)"       : "#ffffff",
    inputBd:   isDark ? "rgba(236,91,19,0.25)"     : "rgba(236,91,19,0.35)",
    rowBg:     isDark ? "rgba(255,255,255,0.04)"   : "rgba(236,91,19,0.04)",
    rowBd:     isDark ? "rgba(255,255,255,0.07)"   : "rgba(236,91,19,0.12)",
    tableBd:   isDark ? "rgba(255,255,255,0.05)"   : "rgba(236,91,19,0.08)",
    tableHd:   isDark ? "rgba(255,255,255,0.07)"   : "rgba(236,91,19,0.1)",
    footerBd:  isDark ? "rgba(255,255,255,0.07)"   : "rgba(236,91,19,0.12)",
    cardBg:    isDark ? "rgba(255,255,255,0.03)"   : "rgba(255,255,255,0.85)",
    cardBd:    isDark ? "rgba(255,255,255,0.1)"    : "rgba(236,91,19,0.18)",
    cardTopBd: isDark ? "rgba(255,255,255,0.06)"   : "rgba(236,91,19,0.1)",
  };
  const glass = isDark
    ? { background:"rgba(34,22,16,0.7)",    backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.2)"  }
    : { background:"rgba(255,255,255,0.88)",backdropFilter:"blur(12px)", WebkitBackdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.22)" };

  const DOC_KEYS = Object.keys(SLOT_META);
  const totalFiles = Object.values(docFiles).flat().length;
  const filledSlots = DOC_KEYS.filter(k => docFiles[k]?.length > 0).length;

  return (
    <div style={{
      minHeight: "100vh",
      background: T.bg,
      fontFamily: "'Public Sans', sans-serif",
      color: T.color,
      display: "flex", flexDirection: "column",
    }}>

      {/* ── Ambient orbs ─────────────────────────────── */}
      <div style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:0, overflow:"hidden" }}>
        {/* Full-width sweep */}
        <div style={{
          position:"absolute", inset:0,
          background:"linear-gradient(95deg, rgba(236,91,19,0.08) 0%, rgba(0,198,255,0.06) 18%, transparent 40%, transparent 60%, rgba(0,198,255,0.07) 82%, rgba(236,91,19,0.08) 100%)",
        }} />

        {/* LEFT — strong orange bloom (mirror of right top) */}
        <div style={{
          position:"absolute", top:"15%", left:"-6%",
          width:isDark?680:500, height:isDark?680:500, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(236,91,19,0.28) 0%,rgba(236,91,19,0.1) 40%,transparent 70%)"
            :"radial-gradient(circle,rgba(236,91,19,0.18) 0%,rgba(236,91,19,0.06) 40%,transparent 70%)",
        }} />
        {/* LEFT — neon cyan bloom bottom (mirror of right bottom) */}
        <div style={{
          position:"absolute", bottom:"0%", left:"8%",
          width:isDark?520:400, height:isDark?520:400, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(0,198,255,0.20) 0%,rgba(0,198,255,0.07) 45%,transparent 70%)"
            :"radial-gradient(circle,rgba(0,198,255,0.10) 0%,rgba(0,198,255,0.03) 45%,transparent 70%)",
        }} />
        {/* LEFT — orange bottom-left corner (mirror of right corner) */}
        <div style={{
          position:"absolute", bottom:"-5%", left:"-2%",
          width:isDark?380:280, height:isDark?380:280, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(236,91,19,0.18) 0%,transparent 65%)"
            :"radial-gradient(circle,rgba(236,91,19,0.10) 0%,transparent 65%)",
        }} />

        {/* RIGHT — strong orange bloom */}
        <div style={{
          position:"absolute", top:"15%", right:"-6%",
          width:isDark?680:500, height:isDark?680:500, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(236,91,19,0.28) 0%,rgba(236,91,19,0.1) 40%,transparent 70%)"
            :"radial-gradient(circle,rgba(236,91,19,0.18) 0%,rgba(236,91,19,0.06) 40%,transparent 70%)",
        }} />
        {/* RIGHT — neon cyan bloom bottom */}
        <div style={{
          position:"absolute", bottom:"0%", right:"8%",
          width:isDark?520:400, height:isDark?520:400, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(0,198,255,0.20) 0%,rgba(0,198,255,0.07) 45%,transparent 70%)"
            :"radial-gradient(circle,rgba(0,198,255,0.10) 0%,rgba(0,198,255,0.03) 45%,transparent 70%)",
        }} />
        {/* RIGHT — orange bottom-right corner */}
        <div style={{
          position:"absolute", bottom:"-5%", right:"-2%",
          width:isDark?380:280, height:isDark?380:280, borderRadius:"50%",
          background:isDark
            ?"radial-gradient(circle,rgba(236,91,19,0.18) 0%,transparent 65%)"
            :"radial-gradient(circle,rgba(236,91,19,0.10) 0%,transparent 65%)",
        }} />
      </div>

      {/* ── Nav ──────────────────────────────────────── */}
      <header style={{
        position:"sticky", top:0, zIndex:50,
        ...glass,
        borderBottom:`1px solid ${T.navBorder}`,
        padding:"14px 80px",
      }}>
        <div style={{
          maxWidth:1280, margin:"0 auto",
          display:"flex", alignItems:"center", justifyContent:"space-between",
        }}>
          {/* Logo + nav links */}
          <div style={{ display:"flex", alignItems:"center", gap:40 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <Icon n="diamond" style={{
                color:"#ec5b13", fontSize:28, lineHeight:1,
              }} />
              <span style={{ fontSize:20, fontWeight:800, letterSpacing:"-0.3px" }}>
                Intelli-Credit
              </span>
            </div>
            <nav style={{ display:"flex", gap:32 }}>
              <a href="#" onClick={e=>{e.preventDefault(); onGoHome();}} style={{
                color:T.linkColor, fontSize:14, fontWeight:600, textDecoration:"none",
                paddingBottom:3, transition:"color .2s",
              }}
                onMouseOver={e=>e.currentTarget.style.color="#ec5b13"}
                onMouseOut={e=>e.currentTarget.style.color=T.linkColor}
              >Home</a>
              <a href="#" onClick={e=>e.preventDefault()} style={{
                color:"#ec5b13", fontSize:14, fontWeight:700, textDecoration:"none",
                borderBottom:"2px solid #ec5b13", paddingBottom:3,
              }}>Analyze</a>
            </nav>
          </div>
          {/* Right */}
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            {/* Theme toggle */}
            <button
              onClick={() => setTheme && setTheme(isDark ? "light" : "dark")}
              style={{
                display:"flex", alignItems:"center", gap:6,
                background: isDark ? "rgba(255,255,255,0.07)" : "rgba(236,91,19,0.1)",
                border:`1px solid ${isDark ? "rgba(255,255,255,0.15)" : "rgba(236,91,19,0.3)"}`,
                borderRadius:20, padding:"6px 16px", cursor:"pointer",
                color: isDark ? "#f1f5f9" : "#ec5b13",
                fontSize:12, fontWeight:700, fontFamily:"'Public Sans',sans-serif",
                transition:"all .2s",
              }}
              title={isDark ? "Switch to Light mode" : "Switch to Dark mode"}
            >
              <Icon n={isDark ? "light_mode" : "dark_mode"} style={{fontSize:16}} />
              {isDark ? "Light" : "Dark"}
            </button>
          </div>
        </div>
      </header>

      <main style={{ flex:1, position:"relative", zIndex:1 }}>

        {/* ── Hero ─────────────────────────────────────── */}
        <section style={{
          padding:"52px 80px 36px",
          maxWidth:1280, margin:"0 auto",
          textAlign:"center",
        }}>
          {/* Badge */}
          <div style={{ marginBottom:16 }}>
            <span style={{
              display:"inline-flex", alignItems:"center", gap:6,
              background:"rgba(236,91,19,0.15)", border:"1px solid rgba(236,91,19,0.4)",
              borderRadius:20, padding:"6px 16px",
              fontSize:11, fontWeight:800, color:"#ec5b13", letterSpacing:"0.1em",
            }}>
              <Icon n="shield" style={{ fontSize:14 }} />
              PREMIUM EDITION
            </span>
          </div>
          <h1 style={{
            fontSize:52, fontWeight:900, letterSpacing:"-1.5px", lineHeight:1.1,
            margin:"0 0 16px",
          }}>
            Document Upload
          </h1>
          <p style={{
            fontSize:16, color:T.muted, maxWidth:600, margin:"0 auto",
            lineHeight:1.7,
          }}>
            Securely submit and manage your corporate filings with military-grade encryption.
            AI analysis starts immediately upon upload.
          </p>
        </section>

        {/* ── Company search panel ─────────────────────── */}
        <section style={{ maxWidth:760, margin:"0 auto 36px", padding:"0 24px" }}>
          <div style={{
            ...glass, borderRadius:20, padding:"28px 32px",
          }}>
            <label style={{
              display:"block", fontSize:11, fontWeight:700, color:T.muted,
              letterSpacing:"0.12em", marginBottom:10, textTransform:"uppercase",
            }}>
              Company Entity Name
            </label>
            <div style={{ position:"relative", marginBottom:20 }}>
              <input
                type="text"
                placeholder="Search registered company (e.g. Acme Corp)"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                style={{
                  width:"100%", padding:"14px 48px 14px 18px",
                  borderRadius:12, border:`1px solid ${T.inputBd}`,
                  background:T.inputBg, color:T.color,
                  fontSize:15, fontFamily:"'Public Sans',sans-serif",
                  outline:"none", boxSizing:"border-box",
                  transition:"border-color .2s, box-shadow .2s",
                }}
                onFocus={e => {
                  e.target.style.borderColor = "rgba(236,91,19,0.7)";
                  e.target.style.boxShadow = isDark
                    ? "inset 0 0 15px rgba(236,91,19,0.08), 0 0 12px rgba(0,198,255,0.12)"
                    : "0 0 0 3px rgba(236,91,19,0.12)";
                }}
                onBlur={e => {
                  e.target.style.borderColor = T.inputBd;
                  e.target.style.boxShadow = "none";
                }}
              />
              <Icon n="search" style={{
                position:"absolute", right:14, top:"50%", transform:"translateY(-50%)",
                color:"#94a3b8", fontSize:20, pointerEvents:"none",
              }} />
            </div>
            {/* Security badge */}
            <div style={{
              display:"inline-flex", alignItems:"center", gap:10,
              background:"rgba(0,198,255,0.07)", border:"1px solid rgba(0,198,255,0.25)",
              borderRadius:12, padding:"10px 16px",
            }}>
              <Icon n="shield" style={{ color:"#00c6ff", fontSize:22 }} />
              <div>
                <div style={{ fontSize:11, fontWeight:700, color:"#cbd5e1", letterSpacing:"0.05em" }}>
                  Security Level
                </div>
                <div style={{ fontSize:12, color:"#00c6ff", fontWeight:600 }}>
                  AES-256 Bit Encrypted
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Document category cards ───────────────────── */}
        <section style={{ maxWidth:1280, margin:"0 auto 36px", padding:"0 24px" }}>
          <div style={{
            display:"grid",
            gridTemplateColumns:"repeat(auto-fill,minmax(210px,1fr))",
            gap:20,
          }}>
            {DOC_KEYS.map((key, si) => {
              const meta = SLOT_META[key];
              const slotFiles = docFiles[key] || [];
              const hasFiles = slotFiles.length > 0;
              const isOver = dragOver === key;
              return (
                <div key={key}
                  style={{
                    ...glass,
                    borderRadius:20, overflow:"hidden",
                    border:`1px solid ${isOver ? meta.color : hasFiles ? meta.color + "60" : T.cardBd}`,
                    background: isOver ? meta.bg : T.cardBg,
                    transition:"all .25s ease",
                    animation:`fadeSlideIn .4s ease ${si * 0.07}s both`,
                  }}
                  onDrop={e => { e.preventDefault(); setDragOver(null); addFiles(key, e.dataTransfer.files); }}
                  onDragOver={e => { e.preventDefault(); setDragOver(key); }}
                  onDragLeave={() => setDragOver(null)}
                >
                  {/* Card top */}
                  <div style={{
                    padding:"28px 20px 20px",
                    textAlign:"center",
                    borderBottom:`1px solid ${hasFiles ? meta.color + "30" : T.cardTopBd}`,
                  }}>
                    <div style={{
                      width:64, height:64, borderRadius:16,
                      background: meta.bg,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      margin:"0 auto 14px",
                    }}>
                      <Icon n={meta.icon} style={{ color: meta.color, fontSize:30 }} />
                    </div>
                    <div style={{ fontSize:14, fontWeight:700, color:T.color, marginBottom:4 }}>
                      {meta.label}
                    </div>
                    <div style={{ fontSize:12, color:T.muted }}>{meta.sub}</div>
                    {hasFiles && (
                      <div style={{
                        display:"inline-block", marginTop:8,
                        background: meta.bg, color: meta.color,
                        borderRadius:20, padding:"2px 12px",
                        fontSize:11, fontWeight:700,
                      }}>{slotFiles.length} file{slotFiles.length > 1 ? "s" : ""} ✓</div>
                    )}
                  </div>
                  {/* Card bottom */}
                  <div style={{ padding:"16px 20px" }}>
                    {slotFiles.length === 0 ? (
                      <div style={{ textAlign:"center" }}>
                        <p style={{ fontSize:11, color:"#64748b", marginBottom:12, lineHeight:1.5 }}>
                          {isOver ? "Drop here!" : "Drag & drop or click to upload"}
                        </p>
                        <input
                          type="file" multiple
                          accept={key === "annual_report" ? ".pdf" : key === "gstr3b" ? ".pdf,.xlsx" : key === "bank_statement" ? ".pdf,.xlsx" : key === "itr6" ? ".pdf,.xml" : ".pdf,.doc,.docx"}
                          id={`up-${key}`} style={{ display:"none" }}
                          onChange={e => addFiles(key, e.target.files)}
                        />
                        <label htmlFor={`up-${key}`} style={{
                          display:"inline-block", padding:"9px 24px",
                          borderRadius:10, cursor:"pointer",
                          fontSize:12, fontWeight:700,
                          border:`1.5px solid ${meta.color}`,
                          color: meta.color, background:"transparent",
                          transition:"background .2s, color .2s",
                        }}
                          onMouseOver={e => {
                            e.currentTarget.style.background = meta.color;
                            e.currentTarget.style.color = "#fff";
                          }}
                          onMouseOut={e => {
                            e.currentTarget.style.background = "transparent";
                            e.currentTarget.style.color = meta.color;
                          }}
                        >
                          UPLOAD
                        </label>
                      </div>
                    ) : (
                      <div>
                        {slotFiles.map((f, fi) => (
                          <div key={fi} style={{
                            display:"flex", alignItems:"center", gap:6,
                            padding:"6px 10px", borderRadius:8, marginBottom:5,
                            background:T.rowBg,
                            border:`1px solid ${T.rowBd}`,
                          }}>
                            <Icon n="picture_as_pdf" style={{ color: meta.color, fontSize:14 }} />
                            <span style={{
                              fontSize:10, color:T.color, flex:1,
                              overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
                            }}>{f.name}</span>
                            <button
                              onClick={() => removeFile(key, fi)}
                              style={{
                                background:"none", border:"none", cursor:"pointer",
                                color:"#64748b", fontSize:15, lineHeight:1, padding:0, flexShrink:0,
                              }}
                            >×</button>
                          </div>
                        ))}
                        <input
                          type="file" multiple
                          accept={key === "annual_report" ? ".pdf" : key === "gstr3b" ? ".pdf,.xlsx" : key === "bank_statement" ? ".pdf,.xlsx" : key === "itr6" ? ".pdf,.xml" : ".pdf,.doc,.docx"}
                          id={`up-${key}-more`} style={{ display:"none" }}
                          onChange={e => addFiles(key, e.target.files)}
                        />
                        <label htmlFor={`up-${key}-more`} style={{
                          display:"block", textAlign:"center", marginTop:6,
                          padding:"5px", borderRadius:8, cursor:"pointer",
                          fontSize:10, fontWeight:600, color: meta.color,
                          border:`1px dashed ${meta.color}60`,
                        }}>+ Add more</label>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Recent Submissions table ──────────────────── */}
        <section style={{ maxWidth:1280, margin:"0 auto 36px", padding:"0 24px" }}>
          <div style={{ ...glass, borderRadius:20, overflow:"hidden" }}>
            {/* Table header row */}
            <div style={{
              display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"20px 28px 16px",
              borderBottom:`1px solid ${T.tableHd}`,
            }}>
              <h3 style={{ margin:0, fontSize:16, fontWeight:700 }}>Recent Submissions</h3>
              <button style={{
                background:"rgba(236,91,19,0.12)", border:"1px solid rgba(236,91,19,0.35)",
                color:"#ec5b13", borderRadius:10, padding:"7px 18px",
                fontSize:12, fontWeight:700, cursor:"pointer", fontFamily:"'Public Sans',sans-serif",
              }}
                onMouseOver={e=>e.currentTarget.style.background="rgba(236,91,19,0.22)"}
                onMouseOut={e=>e.currentTarget.style.background="rgba(236,91,19,0.12)"}
              >View All History</button>
            </div>
            {/* Table head */}
            <div style={{
              display:"grid", gridTemplateColumns:"2fr 1.2fr 1fr 1.2fr",
              padding:"10px 28px",
              fontSize:11, fontWeight:700, color:"#64748b", letterSpacing:"0.08em",
              textTransform:"uppercase",
            }}>
              <span>Document Name</span>
              <span>Category</span>
              <span>Status</span>
              <span>Date Submitted</span>
            </div>
            {/* Row 1 */}
            <div style={{
              display:"grid", gridTemplateColumns:"2fr 1.2fr 1fr 1.2fr",
              padding:"14px 28px", alignItems:"center",
              borderTop:`1px solid ${T.tableBd}`,
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                <Icon n="picture_as_pdf" style={{ color:"#a855f7", fontSize:22 }} />
                <span style={{ fontSize:13, fontWeight:500, color:T.color }}>annual_audit_2023.pdf</span>
              </div>
              <span style={{ fontSize:13, color:"#94a3b8" }}>Annual Report</span>
              <span style={{
                display:"inline-block", padding:"3px 12px", borderRadius:20,
                background:"rgba(74,222,128,0.15)", color:"#4ade80",
                fontSize:11, fontWeight:700, maxWidth:"fit-content",
              }}>VERIFIED</span>
              <span style={{ fontSize:13, color:"#64748b" }}>Oct 12, 2023</span>
            </div>
            {/* Row 2 */}
            <div style={{
              display:"grid", gridTemplateColumns:"2fr 1.2fr 1fr 1.2fr",
              padding:"14px 28px", alignItems:"center",
              borderTop:`1px solid ${T.tableBd}`,
            }}>
              <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                <Icon n="table_chart" style={{ color:"#60a5fa", fontSize:22 }} />
                <span style={{ fontSize:13, fontWeight:500, color:T.color }}>gst_september_r1.xlsx</span>
              </div>
              <span style={{ fontSize:13, color:"#94a3b8" }}>GSTR-3B</span>
              <span style={{
                display:"inline-block", padding:"3px 12px", borderRadius:20,
                background:"rgba(251,191,36,0.15)", color:"#fbbf24",
                fontSize:11, fontWeight:700, maxWidth:"fit-content",
              }}>IN REVIEW</span>
              <span style={{ fontSize:13, color:"#64748b" }}>Oct 15, 2023</span>
            </div>
          </div>
        </section>

        {/* ── Run Analysis button ───────────────────────── */}
        <section style={{ maxWidth:760, margin:"0 auto 52px", padding:"0 24px" }}>
          {/* File chips */}
          {totalFiles > 0 && (
            <div style={{
              display:"flex", gap:8, flexWrap:"wrap", justifyContent:"center", marginBottom:16,
            }}>
              {DOC_KEYS.filter(k => docFiles[k]?.length > 0).map(k => {
                const m = SLOT_META[k];
                return (
                  <span key={k} style={{
                    fontSize:11, padding:"4px 12px", borderRadius:20,
                    background: m.bg, color: m.color, fontWeight:600,
                    border:`1px solid ${m.color}40`,
                  }}>✓ {m.label} ({docFiles[k].length})</span>
                );
              })}
            </div>
          )}
          <button
            onClick={onSubmit}
            disabled={totalFiles === 0}
            style={{
              width:"100%", padding:"17px", borderRadius:16,
              fontWeight:800, fontSize:15, cursor: totalFiles > 0 ? "pointer" : "not-allowed",
              border:"none", fontFamily:"'Public Sans',sans-serif",
              letterSpacing:"0.3px", transition:"transform .15s, background .15s, box-shadow .15s",
              color: totalFiles > 0 ? "white" : (isDark ? "#94a3b8" : "#64748b"),
              background: totalFiles > 0
                ? "linear-gradient(135deg, #ec5b13 0%, #d4420a 100%)"
                : (isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"),
              border: totalFiles > 0 ? "none" : `1px solid ${isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.1)"}`,
              boxShadow: totalFiles > 0 ? "0 4px 20px rgba(236,91,19,0.4)" : "none",
              display:"flex", alignItems:"center", justifyContent:"center", gap:10,
            }}
            onMouseOver={e => { if (totalFiles > 0) e.currentTarget.style.transform = "translateY(-2px)"; }}
            onMouseOut={e => { e.currentTarget.style.transform = "translateY(0)"; }}
          >
            <Icon n="rocket_launch" style={{ fontSize:20 }} />
            {totalFiles === 0
              ? "Upload at least one document to continue"
              : `Run Full AI Appraisal · ${totalFiles} file${totalFiles > 1 ? "s" : ""} across ${filledSlots} categor${filledSlots > 1 ? "ies" : "y"}`}
          </button>
        </section>

      </main>

      {/* ── Footer ───────────────────────────────────── */}
      <footer style={{
        ...glass,
        borderTop:`1px solid ${T.footerBd}`,
        padding:"20px 80px",
        position:"relative", zIndex:1,
      }}>
        <div style={{
          maxWidth:1280, margin:"0 auto",
          display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:12,
        }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <Icon n="security" style={{ color:"#94a3b8", fontSize:18 }} />
            <span style={{ fontSize:12, color:"#64748b" }}>
              Intelli-Credit Analytics · Secure Enterprise Portal
            </span>
          </div>
          <div style={{ display:"flex", gap:20 }}>
            {["Privacy Policy","Terms of Service","Support Center"].map(l => (
              <a key={l} href="#" onClick={e=>e.preventDefault()} style={{
                fontSize:12, color:"#64748b", textDecoration:"none", transition:"color .2s",
              }}
                onMouseOver={e=>e.currentTarget.style.color="#ec5b13"}
                onMouseOut={e=>e.currentTarget.style.color="#64748b"}
              >{l}</a>
            ))}
          </div>
          <span style={{ fontSize:11, color:"#475569" }}>© 2024 Intelli-Credit Edition</span>
        </div>
      </footer>

      {/* ── Keyframe animation (inject once) ─────────── */}
      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
