import { useEffect, useRef, useState } from "react";

const WS_BASE = "ws://127.0.0.1:8000";


const PPE_LABELS = {
  Hard_hat     : "Hard Hat",
  Vest         : "Safety Vest",
  Gloves       : "Gloves",
  Mask         : "Face Mask",
  Safety_boots : "Safety Boots",
};

const ALL_PPE = ["Hard_hat", "Vest", "Gloves", "Mask", "Safety_boots"];

export default function LiveFeed({ cameraId = "CAM_01" }) {
  const [frame,     setFrame]     = useState(null);
  const [missing,   setMissing]   = useState([]);
  const [detected,  setDetected]  = useState([]);
  const [status,    setStatus]    = useState("connecting");
  const [firedNow,  setFiredNow]  = useState(false);
  const [frameCount,setFrameCount]= useState(0);
  const [sourceMode, setSourceMode] = useState("file");
  const wsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;

      const ws = new WebSocket(`${WS_BASE}/ws/stream/${cameraId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) setStatus("connected");
      };

      ws.onmessage = ({ data }) => {
  if (cancelled) return;
  try {
    const d = JSON.parse(data);
    setFrame(d.frame);
    setMissing(d.missing_ppe   || []);
    setDetected(d.detected     || []);
    setSourceMode(d.source_mode || "file");   // ← add this line
    setStatus(d.is_violation ? "violation" : "compliant");
    setFrameCount(c => c + 1);

    if (d.violation_fired) {
      setFiredNow(true);
      setTimeout(() => setFiredNow(false), 1200);
    }
  } catch {}
};

      ws.onclose = () => {
        if (!cancelled) {
          setStatus("connecting");
          setTimeout(connect, 2000);   // auto-reconnect
        }
      };

      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [cameraId]);

  // Status bar config
  const statusConfig = {
    connecting : { bar: "bg-gray-400",  text: "Connecting...",         dot: "bg-gray-300 animate-pulse" },
    connected  : { bar: "bg-blue-500",  text: "Initialising feed...",  dot: "bg-blue-300 animate-pulse" },
    compliant  : { bar: "bg-green-600", text: "All PPE Compliant",     dot: "bg-green-300" },
    violation  : { bar: "bg-red-600",   text: "Violation Detected",    dot: "bg-red-300 animate-ping"   },
  };

  const cfg = statusConfig[status] || statusConfig.connecting;

  return (
    <div className={`rounded-xl overflow-hidden border-2 transition-all duration-300
        ${firedNow ? "border-red-500 shadow-lg shadow-red-200" : "border-gray-200"}`}>

      {/* ── Top status bar ─────────────────────────────── */}
      <div className={`${cfg.bar} px-4 py-2 flex items-center gap-2`}>
        <span className={`w-2.5 h-2.5 rounded-full ${cfg.dot} inline-block`}/>
        <span className="text-white text-sm font-semibold">{cfg.text}</span>
        {missing.length > 0 && (
          <span className="ml-auto text-red-100 text-xs font-medium truncate">
            Missing: {missing.map(m => PPE_LABELS[m] || m).join(", ")}
          </span>
        )}
      </div>

      {/* ── Video frame ────────────────────────────────── */}
      <div className="relative bg-gray-900">
        {frame
          ? <img
              src={`data:image/jpeg;base64,${frame}`}
              alt="Live CCTV feed"
              className="w-full block"
            />
          : <div className="h-52 flex flex-col items-center justify-center text-gray-500 gap-2">
              <div className="w-8 h-8 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin"/>
              <span className="text-sm">Connecting to {cameraId}...</span>
            </div>
        }

        {/* Violation flash overlay */}
        {firedNow && (
          <div className="absolute inset-0 bg-red-500 opacity-20 pointer-events-none animate-ping"/>
        )}

        {/* Frame counter badge */}
        {frame && (
  <div className="absolute bottom-2 left-2 flex items-center gap-2">
    <div className="bg-black bg-opacity-60 text-white text-xs
        px-2 py-0.5 rounded font-mono">
      {cameraId} · {sourceMode === "rtsp" ? "LIVE" : (sourceMode || "file").toUpperCase()}
    </div>
    <div className={`text-xs px-2 py-0.5 rounded font-medium
        ${sourceMode === "rtsp"
          ? "bg-green-500 text-white"
          : "bg-blue-500 text-white"}`}>
      {sourceMode === "rtsp" ? "⬤ LIVE" : "▶ FILE"}
    </div>
  </div>
)}

      </div>

      {/* ── PPE status checklist ───────────────────────── */}
      <div className="bg-gray-50 border-t border-gray-100 px-4 py-3">
        <div className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">
          PPE Status
        </div>
        <div className="grid grid-cols-5 gap-1">
          {ALL_PPE.map(ppe => {
            const present = detected.includes(ppe);
            return (
              <div
                key={ppe}
                className={`flex flex-col items-center gap-1 rounded-lg px-1 py-2
                  ${present ? "bg-green-50" : "bg-red-50"}`}
              >
                <span className={`text-xs font-bold
                  ${present ? "text-green-600" : "text-red-500"}`}>
                  {present ? "✓" : "✗"}
                </span>
                <span className="text-xs text-gray-500 text-center leading-tight">
                  {PPE_LABELS[ppe]}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}