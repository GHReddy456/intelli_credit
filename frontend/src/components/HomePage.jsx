import React, { useEffect, useRef, useState } from "react";

/* ── Load Google Fonts + Material Symbols into <head> ── */
function useFonts() {
  useEffect(() => {
    [
      ["gf-ps", "https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;800;900&display=swap"],
      ["gf-ms", "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"],
    ].forEach(([id, href]) => {
      if (!document.getElementById(id)) {
        const l = document.createElement("link");
        l.id = id; l.rel = "stylesheet"; l.href = href;
        document.head.appendChild(l);
      }
    });
  }, []);
}

/* ── Scroll-reveal hook ── */
function useReveal(threshold = 0.12) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); io.disconnect(); }
    }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, visible };
}
function Reveal({ children, delay = 0, style = {} }) {
  const { ref, visible } = useReveal();
  return (
    <div ref={ref} style={{
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(40px)",
      transition: `opacity .75s cubic-bezier(.4,0,.2,1) ${delay}s, transform .75s cubic-bezier(.4,0,.2,1) ${delay}s`,
      ...style,
    }}>
      {children}
    </div>
  );
}

/* ── Material Symbol icon helper ── */
function Icon({ n, style = {} }) {
  return <span className="material-symbols-outlined" style={{ userSelect:"none", ...style }}>{n}</span>;
}

/* ── Image URLs from the reference design ── */
const IMG = {
  heroBg:    "https://lh3.googleusercontent.com/aida-public/AB6AXuCqPP50oBGMXmyekIg8kd4A4UvdpCgBIXuYmU9yf2DH7NGJ0CirCzKN7qwiY8vxL6WvQ8feXkWVi4gsD0Rq0e0GndJ6lJm_jgilm1xNcHLxphYJA286w6DVu0Oo7HIF3-PuDNgH9XpmNv6-bB2DznnycJ8pn6NSWHJ5W60wHZVwhFJBEE9fIJaJ_-f7NRWJ0Vkjo6kypCRRbSOlAAwh9dexvRFSgRlcz5AhCQLcCwSq5aI6aBhAn6_yxLsgrqIlBDyuKW6JS2qKmtg",
  heroChart: "https://lh3.googleusercontent.com/aida-public/AB6AXuBP9O0ugKB30XK_6L0RbVXyLzIHAmcSSgPFfsHs421EOVgAMvXFxXz8WaFaP39kUFFKrlL_MpqsLKh6wJ1452-1dyUNNaql-kvHvzY4yooa1Q3Dqstrykf8RHl_eEjvRfg6d81h564EjqQV1eY5-3DyWOWi1Qfs1GiKDicyVnbZ8jhWb_gws81u4dm65F9qXA4iCn2UK5bQxMgkIwlOEo2dO8T9sUYFKw1dyM8Fio7jzcMhF_mARLOORhpUY-8G9lo2uRfXPJVu4rg",
  avatar:    "https://lh3.googleusercontent.com/aida-public/AB6AXuA-CJC8bCsHOn8ZF5fjgnyu4eKHy_uFvoHsp8dAM-aWjBoOLwURB8bNgGwP75abwAMnvYTjMYxvtU9ZNN18xeei10bj5f4WA3TGOEKiHCuGbIdxEqGU1vMWFFdzlunvij5LnmgtNHQcXM07MZtXe9PP_g17ttHBBExjdM825Ci8ysq0YInLu1IZJbbk842BSuq81OkYS5Tr61s9MbHgw9oenAF0Pq6fooVsg3bSGJXTwaJDQqIy2wqM0hNIkeMVIYzfMwdxi9_q1yc",
  c1:        "https://lh3.googleusercontent.com/aida-public/AB6AXuB2ANu1WeXXv68ZhXHApmajkV7JjlMeRG6HRuNLe1WGh3YhkJZx067-dKpuAEHdBnh3nOKh5w7pS3RHPbOm68_fQ2O5f50KdWnf1Df2FfnuJCuGTH8lDXC18xDL8AqKoV1aNV0KTNFXTS4H4DifuJzU-O4cUpy7REXINdRx2LSjdtntR_meDNKuJEpUfh2AFw1E9u0AHVQUgdF5ca6dZMKzGyhqOIobJ4MKxcKs8n3GKc-uO0i-w-2SYYoKUmDdWREsXUj2UZg83a4",
  c2:        "https://lh3.googleusercontent.com/aida-public/AB6AXuAr6JmmaekYg6U3xwhXB8WfqS9XUmZ-3XAyIjwVHitX1ZqukZVbYqRZwe8r-Ijfz1nPiILp115Oo8E6DooEzPr3H10Gm-TvqxaNFqs8XqePBEPHZ8xJe8gWwbQvrcVqojct0uP34Lbe3Pjtnos1GWH-27ONNAseNY6x0_CoG-m6mLhObziA5WxufptTMBinQ_d5FBa_NchNLVFvlhZ2y8O1SeG9YmV2RvIFaxrF_5zHEN9eCJW1W4IY8DWht3BxJGLZTyzvKQIvIIE",
  c3:        "https://lh3.googleusercontent.com/aida-public/AB6AXuDkXauj6nEXa7Fz-E4CQyzQz7wU0glWJV3Ban2c6_hgIksWUx3wo_RsEkHCs9V3KgAumBmkjLSAxiEmdiULNJ_chRJAza4S37KHxf4HoitimoI-WsNCPXQpBl3McxH4z2U2qPFGI4Ddael1uMj-RwnHozNrGB8Z5VB3c7Vz9eJI6M0nYfVUDj8WfdeMSCcfO4gGhlImHo99xX5xy8_CrUAnX9RLA-Siu9D1iv8dWRf6qs9lKmN1pilxNGJVR9F1qRKs_DD6B1f2xtA",
  node3d:    "https://lh3.googleusercontent.com/aida-public/AB6AXuBlZWODuJTPwMJQiR-G2eQ0CPagnlZLJ-DrzJYVNBN24U6VW-R1z2ct7YP3xRE1ndO8H2q938oCGYXuWJj3e464bNjzbsYJmJqMPaqOHaSCCHmbir3ibiMx_VpkJMafz0w341zMgT7-LcX8X6sCdjlRE3bVLg1SbDYdIhfBf3etuklMk4cWj_B8zLFoIS0LnEiLSxW8GL-7qIybmQjxESukfsSFH0EbbQViadlJFuyLiWWMiPzfK-z37OVMBFEUmRvmV7jOBiOCdGM",
};

/* ── glass is computed inside the component (theme-aware) ── */

/* ═══════════════════════════════════════
   HOMEPAGE
═══════════════════════════════════════ */
export default function HomePage({ onAnalyze, theme = "dark", setTheme }) {
  useFonts();
  const isDark = theme === "dark";
  const T = {
    bg:        isDark ? "#221610"                    : "#fdf8f2",
    color:     isDark ? "#f1f5f9"                    : "#1a0e06",
    muted:     isDark ? "#94a3b8"                    : "#334155",
    navBg:     isDark ? "rgba(34,22,16,0.88)"        : "rgba(253,248,242,0.96)",
    navBorder: isDark ? "rgba(236,91,19,0.1)"        : "rgba(236,91,19,0.2)",
    searchBg:  isDark ? "rgba(255,255,255,0.05)"     : "rgba(236,91,19,0.07)",
    searchBd:  isDark ? "rgba(255,255,255,0.1)"      : "rgba(236,91,19,0.22)",
    glass:     isDark
      ? { background:"rgba(34,22,16,0.7)",   backdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.2)"  }
      : { background:"rgba(255,255,255,0.85)",backdropFilter:"blur(12px)", border:"1px solid rgba(236,91,19,0.22)" },
    heroGrad:  isDark
      ? `radial-gradient(circle at top right, rgba(236,91,19,0.07), transparent), radial-gradient(circle at bottom left, rgba(34,22,16,1), transparent)`
      : `radial-gradient(circle at top right, rgba(236,91,19,0.12), transparent), radial-gradient(circle at bottom left, #fef0dc, transparent)`,
  };

  return (
    <div className={isDark ? "" : "lt"} style={{
      fontFamily: "'Public Sans', sans-serif",
      background: T.bg, color: T.color,
      minHeight: "100vh", overflowX: "hidden",
      display: "flex", flexDirection: "column",
    }}>
      <style>{`
        /* Material Symbols */
        .material-symbols-outlined {
          font-family: 'Material Symbols Outlined';
          font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
          display: inline-block; line-height: 1;
          vertical-align: middle;
        }
        /* Nav links */
        .hp-nl { font-size:14px; font-weight:500; color:${T.muted};
          text-decoration:none; transition:color .15s; }
        .hp-nl:hover { color:#ec5b13; }
        /* Ghost hero btn */
        .hp-ghost {
          background:${isDark ? "rgba(34,22,16,0.7)" : "rgba(255,255,255,0.88)"}; color:${isDark ? "white" : "#1a0e06"};
          border:1px solid ${isDark ? "rgba(236,91,19,0.2)" : "rgba(236,91,19,0.35)"};
          backdrop-filter:blur(12px); cursor:pointer;
          padding:16px 32px; border-radius:12px;
          font-size:16px; font-weight:700;
          font-family:'Public Sans',sans-serif; transition:background .2s;
        }
        .hp-ghost:hover { background:${isDark ? "rgba(255,255,255,0.1)" : "rgba(236,91,19,0.08)"}; }
        /* Analytics cards */
        .hp-ac { cursor:pointer; }
        .hp-ac-img { width:100%; height:100%; object-fit:cover;
          transition:transform .4s ease; display:block; }
        .hp-ac:hover .hp-ac-img { transform:scale(1.1); }
        /* "View All Features" button */
        .hp-vaf { background:none; border:none; color:#ec5b13; font-weight:700;
          font-family:'Public Sans',sans-serif; font-size:15px; cursor:pointer;
          display:flex; align-items:center; gap:8px; transition:gap .2s; padding:0; }
        .hp-vaf:hover { gap:16px; }
        /* Footer links */
        .hp-fl { color:${T.muted}; font-size:14px; text-decoration:none; transition:color .15s; }
        .hp-fl:hover { color:#ec5b13; }
        @keyframes home-float {
          0%,100% { transform:translateY(0); }
          50%      { transform:translateY(-12px); }
        }
        @keyframes hero-in {
          from { opacity:0; transform:translateY(32px); }
          to   { opacity:1; transform:translateY(0); }
        }
      `}</style>

      {/* ══ NAVIGATION ══════════════════════════════════════════════ */}
      <header style={{
        position:"sticky", top:0, zIndex:50, width:"100%",
        borderBottom:`1px solid ${T.navBorder}`,
        background:T.navBg, backdropFilter:"blur(12px)",
        padding:"16px 80px",
      }}>
        <div style={{
          maxWidth:1280, margin:"0 auto",
          display:"flex", alignItems:"center", justifyContent:"space-between",
        }}>
          {/* Logo + nav */}
          <div style={{ display:"flex", alignItems:"center", gap:40 }}>
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <Icon n="account_balance_wallet"
                style={{ color:"#ec5b13", fontSize:30, lineHeight:1 }} />
              <h2 style={{ fontSize:20, fontWeight:800, letterSpacing:"-0.3px", margin:0 }}>
                Intelli-Credit
              </h2>
            </div>
            <nav style={{ display:"flex", gap:32 }}>
              <a className="hp-nl" href="#" style={{
                color:"#ec5b13", borderBottom:"2px solid #ec5b13",
                paddingBottom:3, fontWeight:700,
              }}>Home</a>
              <a className="hp-nl" href="#" onClick={e=>{e.preventDefault(); onAnalyze();}} style={{
                color:T.color, fontWeight:600, position:"relative",
              }}
                onMouseOver={e=>{e.currentTarget.style.color="#ec5b13";}}
                onMouseOut={e=>{e.currentTarget.style.color=T.color;}}
              >Analyze</a>
            </nav>
          </div>
          {/* Right controls */}
          <div style={{ display:"flex", alignItems:"center", gap:24 }}>
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

      <main style={{ flex:1 }}>

        {/* ══ HERO ══════════════════════════════════════════════════ */}
        <section style={{
          position:"relative", minHeight:"80vh",
          display:"flex", alignItems:"center", padding:"80px 80px",
          background:T.heroGrad,
          overflow:"hidden",
        }}>
          {/* Full-bleed background image */}
          <div style={{
            position:"absolute", inset:0, zIndex:0, opacity:0.15,
            backgroundImage:`url(${IMG.heroBg})`,
            backgroundSize:"cover", backgroundPosition:"center",
            filter:"saturate(0.5) brightness(0.6)",
          }} />

          <div style={{
            maxWidth:1280, margin:"0 auto", width:"100%",
            display:"grid", gridTemplateColumns:"1fr 1fr", gap:48,
            alignItems:"center", position:"relative", zIndex:10,
          }}>

            {/* Left copy */}
            <div style={{
              display:"flex", flexDirection:"column", gap:32,
              animation:"hero-in .7s ease both",
            }}>
              {/* Badge */}
              <div style={{
                display:"inline-flex", alignItems:"center", gap:8,
                padding:"4px 12px", borderRadius:9999,
                background:"rgba(236,91,19,0.1)",
                border:"1px solid rgba(236,91,19,0.2)",
                width:"fit-content",
              }}>
                <Icon n="auto_awesome" style={{ color:"#ec5b13", fontSize:14 }} />
                <span style={{ color:"white", fontSize:11, fontWeight:700,
                  textTransform:"uppercase", letterSpacing:"2px" }}>
                  AI-Powered Risk Engine
                </span>
              </div>

              {/* H1 */}
              <h1 style={{
                fontSize:68, fontWeight:900, lineHeight:1.1,
                letterSpacing:"-2px", color: "white",
                margin:0,
              }}>
                <span style={{ color:"#ec5b13" }}>Intelli-</span>Credit
              </h1>

              <p style={{
                fontSize:19, color: T.muted, lineHeight:1.75, maxWidth:480, margin:0,
              }}>
                Harness AI-driven insights to evaluate credit risks and company
                performance with glass-morphism precision and institutional grade accuracy.
              </p>

              <div style={{ display:"flex", flexWrap:"wrap", gap:16 }}>
                <button onClick={onAnalyze} style={{
                  background:"#ec5b13", color:"white", border:"none", cursor:"pointer",
                  padding:"16px 32px", borderRadius:12, fontSize:16, fontWeight:700,
                  fontFamily:"'Public Sans',sans-serif",
                  display:"flex", alignItems:"center", gap:12,
                  boxShadow:"0 8px 24px rgba(236,91,19,0.2)", transition:"background .2s",
                }}
                  onMouseOver={e=>e.currentTarget.style.background="rgba(236,91,19,0.9)"}
                  onMouseOut={e=>e.currentTarget.style.background="#ec5b13"}
                >
                  <Icon n="bolt" style={{ fontSize:22 }} /> Analyze Now
                </button>
                <button className="hp-ghost">View Full Portfolio</button>
              </div>
            </div>

            {/* Right glass panel */}
            <div style={{ animation:"home-float 7s ease-in-out infinite" }}>
              <div style={{
                ...T.glass, padding:32, borderRadius:24,
                position:"relative", overflow:"hidden",
              }}>
                {/* Watermark icon */}
                <div style={{
                  position:"absolute", top:0, right:0, padding:16, opacity:0.2,
                  pointerEvents:"none",
                }}>
                  <Icon n="monitoring" style={{ color:"#ec5b13", fontSize:96 }} />
                </div>

                <div style={{
                  display:"flex", flexDirection:"column", gap:24,
                  position:"relative", zIndex:10,
                }}>
                  <h3 style={{
                    fontSize:20, fontWeight:700, color: T.color, margin:0,
                    display:"flex", alignItems:"center", gap:8,
                  }}>
                    <Icon n="query_stats" style={{ color:"#ec5b13", fontSize:24 }} />
                    Live Risk Matrix
                  </h3>

                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
                    {[
                      { label:"Stability Score", val:"98.4",  color:"#ec5b13" },
                      { label:"Volatility",      val:"Low",   color:"#ec5b13" },
                    ].map(({ label, val, color }) => (
                      <div key={label} style={{
                        background: isDark ? "rgba(255,255,255,0.05)" : "rgba(236,91,19,0.06)",
                        border: `1px solid ${isDark ? "rgba(255,255,255,0.05)" : "rgba(236,91,19,0.15)"}`,
                        borderRadius:16, padding:16,
                      }}>
                        <p style={{ fontSize:10, color: T.muted, fontWeight:700,
                          textTransform:"uppercase", letterSpacing:"1px",
                          marginBottom:6, marginTop:0 }}>
                          {label}
                        </p>
                        <p style={{ fontSize:26, fontWeight:900, color, margin:0 }}>{val}</p>
                      </div>
                    ))}
                  </div>

                  {/* Chart image */}
                  <div style={{
                    height:192, borderRadius:16, overflow:"hidden",
                    background: isDark ? "rgba(255,255,255,0.05)" : "rgba(236,91,19,0.06)",
                    border: `1px solid ${isDark ? "rgba(255,255,255,0.05)" : "rgba(236,91,19,0.15)"}`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                  }}>
                    <img src={IMG.heroChart} alt="Credit trend chart"
                      style={{ width:"100%", height:"100%",
                        objectFit:"contain", padding:16, opacity:0.8, display:"block" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ══ METRICS BAR ══════════════════════════════════════════ */}
        <section style={{ padding:"0 80px", marginTop:-48, position:"relative", zIndex:20 }}>
          <Reveal>
            <div style={{
              maxWidth:1280, margin:"0 auto",
              display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:24,
            }}>
              {[
                { label:"Credit Accuracy",  val:"99.8%", mi:"verified",
                  delta:"+2.4%", dc:"#34d399", di:"trending_up" },
                { label:"Risk Reduction",   val:"42%",   mi:"security",
                  delta:"-15%",  dc:"#fb923c", di:"trending_down" },
                { label:"Processing Speed", val:"< 2s",  mi:"speed",
                  delta:"+300%", dc:"#34d399", di:"rocket_launch" },
              ].map(({ label, val, mi, delta, dc, di }) => (
                <div key={label} style={{
                  ...T.glass,
                  padding:32, borderRadius:16,
                  display:"flex", flexDirection:"column", gap:8,
                }}>
                  <div style={{ display:"flex", justifyContent:"space-between",
                    alignItems:"center" }}>
                    <span style={{ color: T.muted, fontSize:14, fontWeight:500 }}>
                      {label}
                    </span>
                    <Icon n={mi} style={{ color:"#ec5b13", fontSize:24 }} />
                  </div>
                  <div style={{ display:"flex", alignItems:"baseline", gap:8 }}>
                    <span style={{ fontSize:32, fontWeight:900, color: T.color }}>{val}</span>
                    <span style={{
                      color:dc, fontSize:13, fontWeight:700,
                      display:"flex", alignItems:"center", gap:2,
                    }}>
                      <Icon n={di} style={{ fontSize:14 }} />{delta}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </section>

        {/* ══ ANALYTICS ════════════════════════════════════════════ */}
        <section style={{ padding:"96px 80px", background: T.bg }}>
          <div style={{ maxWidth:1280, margin:"0 auto" }}>
            <Reveal>
              <div style={{
                display:"flex", justifyContent:"space-between",
                alignItems:"flex-end", gap:32, marginBottom:64, flexWrap:"wrap",
              }}>
                <div style={{ maxWidth:640 }}>
                  <h2 style={{
                    fontSize:48, fontWeight:900, color: T.color,
                    lineHeight:1.1, letterSpacing:"-1.5px",
                    marginTop:0, marginBottom:24,
                  }}>
                    Institutional Grade Analytics
                  </h2>
                  <p style={{ fontSize:18, color: T.muted, lineHeight:1.7, margin:0 }}>
                    Leverage our proprietary AI models to gain a competitive edge in credit
                    assessment through deep-learning data pipelines.
                  </p>
                </div>
                <button className="hp-vaf">
                  View All Features <Icon n="arrow_forward" style={{ fontSize:20 }} />
                </button>
              </div>
            </Reveal>

            <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:32 }}>
              {[
                { src:IMG.c1, title:"Real-time Risk Scoring",
                  desc:"Instant analysis of thousands of data points across global markets with millisecond latency." },
                { src:IMG.c2, title:"Predictive Performance",
                  desc:"Forecast company performance with high precision using ensemble neural network modeling." },
                { src:IMG.c3, title:"Market Correlation",
                  desc:"Understand global trends and macro-economic factors impacting your specific institutional portfolio." },
              ].map(({ src, title, desc }, i) => (
                <Reveal key={title} delay={i * 0.12}>
                  <div className="hp-ac">
                    <div style={{
                      aspectRatio:"16/9", borderRadius:16, overflow:"hidden",
                      marginBottom:24, border:`1px solid ${isDark ? "rgba(255,255,255,0.05)" : "rgba(236,91,19,0.12)"}`,
                      position:"relative",
                    }}>
                      <img src={src} alt={title} className="hp-ac-img" />
                      <div style={{
                        position:"absolute", inset:0,
                        background:`linear-gradient(to top, ${isDark ? "#221610" : "#fdf8f2"} 0%, transparent 60%)`,
                        pointerEvents:"none",
                      }} />
                    </div>
                    <h4 style={{ fontSize:20, fontWeight:700, color: T.color,
                      marginBottom:8, marginTop:0 }}>{title}</h4>
                    <p style={{ fontSize:14, color: T.muted, lineHeight:1.7, margin:0 }}>
                      {desc}
                    </p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ══ STRATEGIC INSIGHTS ═══════════════════════════════════ */}
        <section style={{ padding:"0 80px 128px" }}>
          <Reveal>
            <div style={{ maxWidth:1280, margin:"0 auto" }}>
              <div style={{
                ...T.glass, borderRadius:24, padding:48,
                overflow:"hidden", position:"relative",
              }}>
                {/* Orange glow orb – top right */}
                <div style={{
                  position:"absolute", top:-80, right:-80,
                  width:384, height:384, borderRadius:"50%",
                  background:"rgba(236,91,19,0.2)", filter:"blur(48px)",
                  pointerEvents:"none",
                }} />

                <div style={{
                  position:"relative", zIndex:10,
                  display:"flex", flexDirection:"row",
                  alignItems:"center", gap:48, flexWrap:"wrap",
                }}>
                  {/* Left text */}
                  <div style={{ flex:"1 1 360px" }}>
                    <h2 style={{ fontSize:38, fontWeight:700, color: T.color,
                      marginTop:0, marginBottom:24 }}>
                      Strategic Portfolio Insights
                    </h2>
                    <p style={{ fontSize:18, color: T.muted,
                      lineHeight:1.8, marginBottom:32, marginTop:0 }}>
                      Access institutional-level clarity on complex assets. Our platform
                      transforms raw financial data into actionable strategic intelligence.
                    </p>
                    <ul style={{
                      listStyle:"none", padding:0,
                      margin:"0 0 40px 0",
                      display:"flex", flexDirection:"column", gap:16,
                    }}>
                      {[
                        "Automated Due Diligence Workflows",
                        "Customizable Risk Threshold Alerts",
                        "Regulatory Compliance Monitoring",
                      ].map(item => (
                        <li key={item} style={{
                          display:"flex", alignItems:"center", gap:12,
                          color: T.muted, fontSize:16,
                        }}>
                          <Icon n="check_circle" style={{ color:"#ec5b13", fontSize:22 }} />
                          {item}
                        </li>
                      ))}
                    </ul>
                    <button onClick={onAnalyze} style={{
                      background: isDark ? "white" : "#221610",
                      color: isDark ? "#221610" : "white",
                      border:"none", cursor:"pointer",
                      padding:"16px 32px", borderRadius:12, fontSize:16, fontWeight:900,
                      fontFamily:"'Public Sans',sans-serif", transition:"background .2s",
                    }}
                      onMouseOver={e=>e.currentTarget.style.background= isDark ? "#e2e8f0" : "#ec5b13"}
                      onMouseOut={e=>e.currentTarget.style.background= isDark ? "white" : "#221610"}
                    >
                      Get Started
                    </button>
                  </div>

                  {/* Right 3D image */}
                  <div style={{
                    flex:"1 1 360px",
                    display:"flex", justifyContent:"center",
                  }}>
                    <div style={{ width:"100%", maxWidth:400, aspectRatio:"1" }}>
                      <img src={IMG.node3d} alt="3D data node visualization"
                        style={{ width:"100%", height:"100%", objectFit:"contain",
                          display:"block", animation:"home-float 8s ease-in-out 1s infinite" }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </section>

      </main>

      {/* ══ FOOTER ═══════════════════════════════════════════════ */}
      <footer style={{
        borderTop:`1px solid ${T.navBorder}`,
        background: T.bg, padding:"48px 80px",
      }}>
        <div style={{
          maxWidth:1280, margin:"0 auto",
          display:"flex", justifyContent:"space-between", alignItems:"center",
          flexWrap:"wrap", gap:32,
        }}>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <Icon n="account_balance_wallet" style={{ color:"#ec5b13", fontSize:24 }} />
            <span style={{ fontSize:18, fontWeight:800, letterSpacing:"-0.3px" }}>
              Intelli-Credit
            </span>
          </div>
          <div style={{ display:"flex", gap:40 }}>
            {["Privacy Policy","Terms of Service","Contact Support"].map(l => (
              <a key={l} className="hp-fl" href="#">{l}</a>
            ))}
          </div>
          <p style={{ fontSize:13, color: T.muted, margin:0 }}>
            © 2024 Intelli-Credit Analytics. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
