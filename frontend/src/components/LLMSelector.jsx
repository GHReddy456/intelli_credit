import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API = axios.create({ baseURL: "/api" });

/**
 * Compact CPU / GPU toggle shown in the app header.
 * Calls GET /api/llm/config on mount to read current state.
 * Calls POST /api/llm/config {"device": "cpu"|"gpu"} on toggle.
 */
export default function LLMSelector() {
  const [device,  setDevice]  = useState("cpu");
  const [model,   setModel]   = useState("phi3:mini");
  const [ollamaOK, setOllamaOK] = useState(null);   // null=loading, true=ok, false=offline
  const [loading,  setLoading]  = useState(false);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await API.get("/llm/config");
      setDevice(res.data.device);
      setModel(res.data.model);
      setOllamaOK(res.data.ollama_running);
    } catch {
      setOllamaOK(false);
    }
  }, []);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const toggle = async (next) => {
    if (next === device || loading) return;
    setLoading(true);
    try {
      const res = await API.post("/llm/config", { device: next });
      setDevice(res.data.device);
      setModel(res.data.model);
      // Re-ping Ollama status after switch
      const cfg = await API.get("/llm/config");
      setOllamaOK(cfg.data.ollama_running);
    } catch {
      /* silently ignore — backend logs it */
    } finally {
      setLoading(false);
    }
  };

  /* ── status dot ─────────────────────────────────────── */
  const dotColor =
    ollamaOK === null  ? "#94A3B8" :   // loading
    ollamaOK           ? "#10B981" :   // green — Ollama online
                         "#EF4444";    // red   — Ollama offline

  const dotTitle =
    ollamaOK === null  ? "Checking Ollama…" :
    ollamaOK           ? "Ollama online"    :
                         "Ollama offline — LLM disabled (rule-based fallbacks active)";

  /* ── pill styles ─────────────────────────────────────── */
  const pillBase = {
    padding:      "4px 12px",
    borderRadius: 20,
    fontSize:     11,
    fontWeight:   700,
    cursor:       loading ? "not-allowed" : "pointer",
    transition:   "all 0.2s ease",
    border:       "1px solid transparent",
    userSelect:   "none",
    letterSpacing: "0.5px",
  };

  const cpuActive = {
    ...pillBase,
    background:  "linear-gradient(135deg,#36cceb,#0891b2)",
    color:       "#fff",
    boxShadow:   "0 0 10px rgba(54,204,235,0.4)",
  };
  const gpuActive = {
    ...pillBase,
    background:  "linear-gradient(135deg,#a855f7,#7c3aed)",
    color:       "#fff",
    boxShadow:   "0 0 10px rgba(168,85,247,0.4)",
  };
  const inactive = {
    ...pillBase,
    background:  "rgba(30,41,59,0.6)",
    color:       "#64748B",
    border:      "1px solid rgba(100,116,139,0.3)",
  };

  return (
    <div style={{
      display:       "flex",
      alignItems:    "center",
      gap:           8,
      padding:       "6px 10px",
      borderRadius:  12,
      background:    "rgba(15,23,42,0.6)",
      border:        "1px solid rgba(54,204,235,0.18)",
      backdropFilter:"blur(8px)",
    }}>
      {/* Ollama status dot */}
      <div
        title={dotTitle}
        style={{
          width:     7, height: 7, borderRadius: "50%",
          background: dotColor,
          boxShadow:  ollamaOK ? `0 0 6px ${dotColor}` : "none",
          flexShrink: 0,
          animation:  ollamaOK === null ? "pulse-dot 1.5s ease-in-out infinite" : "none",
        }}
      />

      {/* Label */}
      <span style={{ fontSize: 10, color: "#64748B", whiteSpace: "nowrap" }}>LLM</span>

      {/* Toggle pills */}
      <div style={{ display: "flex", gap: 4 }}>
        <div
          style={device === "cpu" ? cpuActive : inactive}
          onClick={() => toggle("cpu")}
          title="CPU mode — phi3:mini (~15-20 tok/s on i7-13th gen)"
        >
          CPU
        </div>
        <div
          style={device === "gpu" ? gpuActive : inactive}
          onClick={() => toggle("gpu")}
          title="GPU mode — llama3.1:8b (~70 tok/s on RTX 4060 8 GB)"
        >
          GPU
        </div>
      </div>

      {/* Active model name */}
      <span style={{
        fontSize:   9,
        color:      "#475569",
        whiteSpace: "nowrap",
        fontFamily: "monospace",
        maxWidth:   90,
        overflow:   "hidden",
        textOverflow: "ellipsis",
      }}>
        {loading ? "switching…" : model}
      </span>
    </div>
  );
}
