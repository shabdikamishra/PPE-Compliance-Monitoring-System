import { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler
} from "chart.js";
import { Bar, Line, Doughnut } from "react-chartjs-2";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler
);

const API = "http://127.0.0.1:8000";

const PPE_LABELS = {
  Hard_hat     : "Hard Hat",
  Vest         : "Safety Vest",
  Gloves       : "Gloves",
  Mask         : "Face Mask",
  Safety_boots : "Safety Boots",
};

const CHART_COLORS = [
  "#3B82F6", "#EF4444", "#F59E0B",
  "#10B981", "#8B5CF6", "#EC4899",
];

// ── Shared chart options ───────────────────────────────────
const baseOptions = {
  responsive       : true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor : "#1E293B",
      titleColor      : "#F1F5F9",
      bodyColor       : "#CBD5E1",
      padding         : 10,
      cornerRadius    : 8,
      displayColors   : false,
    },
  },
  scales: {
    x: {
      grid : { display: false },
      ticks: { color: "#94A3B8", font: { size: 11 } },
      border: { display: false },
    },
    y: {
      grid : { color: "#F1F5F9" },
      ticks: {
        color     : "#94A3B8",
        font      : { size: 11 },
        stepSize  : 1,
        precision : 0,
      },
      border: { display: false },
      beginAtZero: true,
    },
  },
};

// ── Compliance Score Ring ──────────────────────────────────
function ComplianceRing({ score, rating }) {
  const remaining = 100 - score;
  const color =
    score >= 90 ? "#10B981" :
    score >= 75 ? "#F59E0B" :
    score >= 60 ? "#F97316" : "#EF4444";

  const data = {
    datasets: [{
      data           : [score, remaining],
      backgroundColor: [color, "#F1F5F9"],
      borderWidth    : 0,
      cutout         : "80%",
    }],
  };

  const options = {
    responsive          : true,
    maintainAspectRatio : false,
    plugins             : { legend: { display: false }, tooltip: { enabled: false } },
  };

  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <div className="relative w-32 h-32">
        <Doughnut data={data} options={options} />
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>
            {score}%
          </span>
          <span className="text-xs text-gray-400">compliance</span>
        </div>
      </div>
      <div className={`text-xs font-semibold px-3 py-1 rounded-full
        ${score >= 90 ? "bg-green-100 text-green-700"  :
          score >= 75 ? "bg-yellow-100 text-yellow-700":
          score >= 60 ? "bg-orange-100 text-orange-700":
                        "bg-red-100 text-red-700"}`}>
        {rating}
      </div>
    </div>
  );
}

// ── Daily violations bar chart ─────────────────────────────
function DailyChart({ daily }) {
  if (!daily?.length) return <EmptyChart label="No data yet" />;

  const data = {
    labels  : daily.map(d => d.date),
    datasets: [{
      label          : "Violations",
      data           : daily.map(d => d.count),
      backgroundColor: daily.map(d =>
        d.count === 0 ? "#DCFCE7" :
        d.count <= 3  ? "#FEF9C3" : "#FEE2E2"
      ),
      borderColor    : daily.map(d =>
        d.count === 0 ? "#16A34A" :
        d.count <= 3  ? "#CA8A04" : "#DC2626"
      ),
      borderWidth    : 1.5,
      borderRadius   : 6,
      borderSkipped  : false,
    }],
  };

  return (
    <div style={{ height: 180 }}>
      <Bar data={data} options={{
        ...baseOptions,
        plugins: {
          ...baseOptions.plugins,
          tooltip: {
            ...baseOptions.plugins.tooltip,
            callbacks: {
              label: ctx => ` ${ctx.parsed.y} violation${ctx.parsed.y !== 1 ? "s" : ""}`,
            },
          },
        },
      }} />
    </div>
  );
}

// ── Violations trend line chart ────────────────────────────
function TrendLine({ daily }) {
  if (!daily?.length) return <EmptyChart label="No data yet" />;

  const data = {
    labels  : daily.map(d => d.date),
    datasets: [{
      label          : "Violations",
      data           : daily.map(d => d.count),
      borderColor    : "#3B82F6",
      backgroundColor: "rgba(59,130,246,0.08)",
      borderWidth    : 2.5,
      pointBackgroundColor: "#3B82F6",
      pointRadius    : 4,
      pointHoverRadius: 6,
      fill           : true,
      tension        : 0.4,
    }],
  };

  return (
    <div style={{ height: 180 }}>
      <Line data={data} options={baseOptions} />
    </div>
  );
}

// ── PPE breakdown horizontal bars ─────────────────────────
function PPEBreakdown({ byPpe }) {
  if (!byPpe?.length) return <EmptyChart label="No violations recorded" />;

  const sorted = [...byPpe].sort((a, b) => b.count - a.count);
  const max    = Math.max(...sorted.map(d => d.count), 1);

  return (
    <div className="space-y-2 py-2" style={{ minHeight: 180 }}>
      {sorted.map((item, i) => {
        const pct   = (item.count / max) * 100;
        const label = PPE_LABELS[item.ppe] || item.ppe;
        return (
          <div key={item.ppe} className="flex items-center gap-3">
            <div className="w-24 text-xs text-gray-500 text-right flex-shrink-0">
              {label}
            </div>
            <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
              <div
                className="h-full rounded-full flex items-center justify-end pr-2
                    transition-all duration-700"
                style={{
                  width           : `${Math.max(pct, 8)}%`,
                  backgroundColor : CHART_COLORS[i % CHART_COLORS.length],
                  transitionDelay : `${i * 80}ms`,
                }}
              >
                <span className="text-white text-xs font-medium">{item.count}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Camera breakdown doughnut ──────────────────────────────
function CameraChart({ byCamera }) {
  if (!byCamera?.length) return <EmptyChart label="No data yet" />;

  const data = {
    labels  : byCamera.map(d => d.camera),
    datasets: [{
      data           : byCamera.map(d => d.count),
      backgroundColor: CHART_COLORS.slice(0, byCamera.length),
      borderWidth    : 0,
      hoverOffset    : 8,
    }],
  };

  const options = {
    responsive          : true,
    maintainAspectRatio : false,
    cutout              : "60%",
    plugins: {
      legend: {
        display  : true,
        position : "right",
        labels   : {
          color    : "#64748B",
          font     : { size: 11 },
          padding  : 12,
          boxWidth : 12,
          boxHeight: 12,
        },
      },
      tooltip: {
        ...baseOptions.plugins.tooltip,
        callbacks: {
          label: ctx => ` ${ctx.label}: ${ctx.parsed} violations`,
        },
      },
    },
  };

  return (
    <div style={{ height: 180 }}>
      <Doughnut data={data} options={options} />
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────
function EmptyChart({ label }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 text-gray-400"
         style={{ height: 180 }}>
      <div className="text-3xl">📊</div>
      <div className="text-sm">{label}</div>
    </div>
  );
}

// ── Loading skeleton ───────────────────────────────────────
function ChartSkeleton() {
  return (
    <div className="animate-pulse" style={{ height: 180 }}>
      <div className="h-full bg-gray-100 rounded-xl"/>
    </div>
  );
}

// ── Tab button ─────────────────────────────────────────────
function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-full font-medium
          transition-all duration-150
          ${active
            ? "bg-blue-600 text-white shadow-sm"
            : "bg-gray-100 text-gray-500 hover:bg-gray-200"}`}
    >
      {children}
    </button>
  );
}

// ── Main AnalyticsPanel ────────────────────────────────────
export default function AnalyticsPanel() {
  const [score,    setScore]    = useState(null);
  const [trends,   setTrends]   = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [chartTab, setChartTab] = useState("bar");
  const [dataTab,  setDataTab]  = useState("daily");

  const fetchData = () => {
    Promise.all([
      axios.get(`${API}/api/compliance-score`).catch(() => null),
      axios.get(`${API}/api/trends`).catch(() => null),
    ]).then(([scoreRes, trendsRes]) => {
      if (scoreRes)  setScore(scoreRes.data);
      if (trendsRes) setTrends(trendsRes.data);
      setLoading(false);
    });
  };

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 15000);
    return () => clearInterval(t);
  }, []);

  const renderChart = () => {
    if (loading) return <ChartSkeleton />;

    if (dataTab === "daily") {
      return chartTab === "bar"
        ? <DailyChart daily={trends?.daily} />
        : <TrendLine  daily={trends?.daily} />;
    }
    if (dataTab === "ppe")    return <PPEBreakdown byPpe={trends?.by_ppe} />;
    if (dataTab === "camera") return <CameraChart  byCamera={trends?.by_camera} />;
    return null;
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

      {/* ── Header ─────────────────────────────────────── */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-100">
        <div className="flex items-start justify-between gap-4">

          {/* Left — title */}
          <div>
            <h2 className="text-sm font-semibold text-gray-800">
              Analytics &amp; Compliance
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Live data · refreshes every 15s
            </p>
          </div>

          {/* Right — compliance ring */}
          {loading
            ? <div className="w-32 h-32 bg-gray-100 rounded-full animate-pulse"/>
            : score && (
                <ComplianceRing
                  score={score.score}
                  rating={score.rating}
                />
              )
          }
        </div>

        {/* PPE violation pills */}
        {!loading && score?.ppe_breakdown &&
          Object.keys(score.ppe_breakdown).length > 0 && (
          <div className="mt-4">
            <div className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wide">
              Most violated PPE today
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(score.ppe_breakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([ppe, count]) => (
                  <span key={ppe}
                    className="inline-flex items-center gap-1.5 text-xs
                        bg-red-50 text-red-600 border border-red-100
                        px-2.5 py-1 rounded-full font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400"/>
                    {PPE_LABELS[ppe] || ppe}
                    <span className="bg-red-100 text-red-700 rounded-full
                        px-1.5 font-bold text-xs">
                      {count}
                    </span>
                  </span>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Chart area ─────────────────────────────────── */}
      <div className="px-5 pt-4 pb-5">

        {/* Control row */}
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">

          {/* Data selector */}
          <div className="flex gap-1">
            <TabBtn active={dataTab === "daily"}
                    onClick={() => setDataTab("daily")}>
              Daily trend
            </TabBtn>
            <TabBtn active={dataTab === "ppe"}
                    onClick={() => setDataTab("ppe")}>
              By PPE type
            </TabBtn>
            <TabBtn active={dataTab === "camera"}
                    onClick={() => setDataTab("camera")}>
              By camera
            </TabBtn>
          </div>

          {/* Chart type toggle — only show for daily */}
          {dataTab === "daily" && (
            <div className="flex gap-1 bg-gray-100 rounded-full p-0.5">
              <button
                onClick={() => setChartTab("bar")}
                title="Bar chart"
                className={`text-xs px-3 py-1 rounded-full transition-all
                    ${chartTab === "bar"
                      ? "bg-white text-gray-700 shadow-sm"
                      : "text-gray-400 hover:text-gray-600"}`}>
                ▐▐ Bar
              </button>
              <button
                onClick={() => setChartTab("line")}
                title="Line chart"
                className={`text-xs px-3 py-1 rounded-full transition-all
                    ${chartTab === "line"
                      ? "bg-white text-gray-700 shadow-sm"
                      : "text-gray-400 hover:text-gray-600"}`}>
                ∿ Line
              </button>
            </div>
          )}
        </div>

        {/* Chart */}
        {renderChart()}

        {/* Chart legend / footnote */}
        <div className="mt-3 text-xs text-gray-400">
          {dataTab === "daily" && "Bar color: green = no violations · yellow = 1–3 · red = 4+"}
          {dataTab === "ppe"   && "Number of times each PPE item was found missing"}
          {dataTab === "camera"&& "Total violations detected per camera feed"}
        </div>
      </div>
    </div>
  );
}