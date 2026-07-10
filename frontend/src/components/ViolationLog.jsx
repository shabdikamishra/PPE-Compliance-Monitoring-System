import { useEffect, useState } from "react";
import axios from "axios";
import { exportToCSV } from "../utils/export";

const API = "http://127.0.0.1:8000";
const PPE_LABELS = {
  Hard_hat: "Hard Hat", Vest: "Safety Vest",
  Gloves: "Gloves", Mask: "Face Mask", Safety_boots: "Safety Boots"
};

const CAMERAS  = ["All", "CAM_01", "CAM_02", "CAM_03"];
const PPE_KEYS = ["All", "Hard_hat", "Vest", "Gloves", "Mask", "Safety_boots"];

function timeAgo(isoString) {
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 60)   return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return new Date(isoString).toLocaleTimeString("en-IN");
}

export default function ViolationLog() {
  const [violations, setViolations] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [newId,      setNewId]      = useState(null);
  const [camera,     setCamera]     = useState("All");
  const [ppeFilter,  setPpeFilter]  = useState("All");
  const [showResolved, setShowResolved] = useState(false);

  const fetchViolations = async () => {
    try {
      const params = {};
      if (camera   !== "All") params.camera_id = camera;
      if (ppeFilter !== "All") params.ppe_type = ppeFilter;

      const r = await axios.get(`${API}/api/violations/filtered`, { params });
      setViolations(prev => {
        if (prev.length > 0 && r.data.length > 0 && r.data[0].id !== prev[0]?.id) {
          setNewId(r.data[0].id);
          setTimeout(() => setNewId(null), 2000);
        }
        return r.data;
      });
      setLoading(false);
    } catch {
      // fallback to basic endpoint
      const r = await axios.get(`${API}/api/violations`).catch(() => ({ data: [] }));
      setViolations(r.data);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchViolations();
    const t = setInterval(fetchViolations, 5000);
    return () => clearInterval(t);
  }, [camera, ppeFilter]);

  const handleResolve = async (id) => {
    try {
      await axios.patch(`${API}/api/violations/${id}/resolve`, { notes: "Resolved via dashboard" });
      setViolations(prev => prev.map(v =>
        v.id === id ? { ...v, resolved: true } : v
      ));
    } catch {}
  };

  const displayed = violations.filter(v => showResolved ? true : !v.resolved);

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden flex flex-col">

      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="font-semibold text-gray-800 text-sm">Violation Log</div>
            <div className="text-xs text-gray-400">{displayed.length} events</div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => exportToCSV(violations)}
              className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600
                  px-3 py-1.5 rounded-lg font-medium transition-colors">
              Export CSV
            </button>
            <button
              onClick={() => setShowResolved(s => !s)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors
                ${showResolved
                  ? "bg-blue-100 text-blue-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {showResolved ? "Hide resolved" : "Show resolved"}
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          <select
            value={camera}
            onChange={e => setCamera(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5
                bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-300">
            {CAMERAS.map(c => <option key={c} value={c}>{c === "All" ? "All cameras" : c}</option>)}
          </select>
          <select
            value={ppeFilter}
            onChange={e => setPpeFilter(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1.5
                bg-white text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-300">
            {PPE_KEYS.map(p => (
              <option key={p} value={p}>{p === "All" ? "All PPE types" : PPE_LABELS[p] || p}</option>
            ))}
          </select>
        </div>
      </div>

      {/* List */}
      <div className="divide-y divide-gray-50 overflow-y-auto flex-1 max-h-96">
        {loading && (
          <div className="p-6 flex items-center justify-center gap-2 text-gray-400">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-400 rounded-full animate-spin"/>
            <span className="text-sm">Loading...</span>
          </div>
        )}

        {!loading && displayed.length === 0 && (
          <div className="p-8 text-center">
            <div className="text-3xl mb-2">✅</div>
            <div className="text-sm font-medium text-gray-500">No violations</div>
          </div>
        )}

        {displayed.map(v => (
          <div
            key={v.id}
            className={`p-3 flex gap-3 transition-all duration-500
              ${v.id === newId ? "bg-red-50 border-l-4 border-l-red-500" : ""}
              ${v.resolved     ? "opacity-50"  : "hover:bg-gray-50"}`}
          >
            {v.image_url
              ? <img src={v.image_url} alt="snapshot"
                     className="w-16 h-12 object-cover rounded-lg flex-shrink-0
                         border border-gray-100"
                     onError={e => { e.target.style.display = 'none'; }}/>
              : <div className="w-16 h-12 bg-gray-100 rounded-lg flex-shrink-0
                    flex items-center justify-center text-gray-300 text-xl">📷</div>
            }

            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-1">
                <div className="text-sm font-medium text-red-600 truncate">
                  {v.missing_ppe?.map(p => PPE_LABELS[p] || p).join(", ")}
                </div>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {timeAgo(v.timestamp)}
                </span>
              </div>
              <div className="text-xs text-gray-400 mt-0.5">
                {v.camera_id} · {new Date(v.timestamp).toLocaleString("en-IN")}
              </div>
              <div className="flex items-center gap-2 mt-1">
                {v.resolved
                  ? <span className="text-xs bg-green-50 text-green-600
                        border border-green-100 px-2 py-0.5 rounded-full">
                      ✓ Resolved
                    </span>
                  : <button
                      onClick={() => handleResolve(v.id)}
                      className="text-xs bg-gray-100 hover:bg-green-50
                          hover:text-green-700 text-gray-500 px-2 py-0.5
                          rounded-full transition-colors">
                      Mark resolved
                    </button>
                }
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
        <div className="text-xs text-gray-400 text-center">
          {displayed.length} of {violations.length} violations shown
        </div>
      </div>
    </div>
  );
}