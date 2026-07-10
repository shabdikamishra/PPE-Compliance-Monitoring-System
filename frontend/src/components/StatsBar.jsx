import { useEffect, useState, useRef } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function StatsBar() {
  const [stats, setStats]   = useState({ total: 0, today: 0, cameras_active: 1 });
  const [flash, setFlash]   = useState(false);
  const prevToday           = useRef(0);

  const fetchStats = () => {
    axios.get(`${API}/api/stats`)
      .then(r => setStats(r.data))
      .catch(() => {});
  };

  useEffect(() => {
    fetchStats();
    const t = setInterval(fetchStats, 5000);
    return () => clearInterval(t);
  }, []);

  // Flash animation when today's count increases
  useEffect(() => {
    if (stats.today > prevToday.current) {
      setFlash(true);
      setTimeout(() => setFlash(false), 800);
    }
    prevToday.current = stats.today;
  }, [stats.today]);

  const cards = [
    {
      label   : "Total Violations",
      value   : stats.total,
      color   : "text-gray-800",
      bg      : "bg-white",
      icon    : "⚠",
      iconBg  : "bg-red-100",
      iconColor: "text-red-500",
    },
    {
      label   : "Today",
      value   : stats.today,
      color   : flash ? "text-red-600 scale-110" : "text-red-600",
      bg      : flash ? "bg-red-50" : "bg-white",
      icon    : "📅",
      iconBg  : "bg-orange-100",
      iconColor: "text-orange-500",
    },
    {
      label   : "Cameras Active",
      value   : stats.cameras_active ?? 1,
      color   : "text-green-600",
      bg      : "bg-white",
      icon    : "📷",
      iconBg  : "bg-green-100",
      iconColor: "text-green-500",
    },
    {
      label   : "PPE Items Monitored",
      value   : stats.required_ppe?.length ?? 5,
      color   : "text-blue-600",
      bg      : "bg-white",
      icon    : "🦺",
      iconBg  : "bg-blue-100",
      iconColor: "text-blue-500",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {cards.map(({ label, value, color, bg, icon, iconBg, iconColor }) => (
        <div
          key={label}
          className={`${bg} rounded-xl border border-gray-200 p-4 flex items-center gap-3 transition-all duration-300`}
        >
          <div className={`${iconBg} rounded-lg p-2 text-lg ${iconColor}`}>
            {icon}
          </div>
          <div>
            <div className="text-xs text-gray-400 font-medium">{label}</div>
            <div className={`text-2xl font-semibold transition-all duration-300 ${color}`}>
              {value}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}