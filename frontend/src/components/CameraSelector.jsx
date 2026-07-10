const CAMERAS = [
  { id: "CAM_01", name: "Main Entrance",   zone: "Gate A",  icon: "🏭" },
  { id: "CAM_02", name: "Production Floor", zone: "Zone B", icon: "⚙️" },
  { id: "CAM_03", name: "Loading Bay",      zone: "Zone C", icon: "🚚" },
];

export default function CameraSelector({ selected, onSelect }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="font-semibold text-gray-800 text-sm">Cameras</div>
        <div className="text-xs text-gray-400 mt-0.5">Select to monitor</div>
      </div>
      <div className="divide-y divide-gray-50">
        {CAMERAS.map(cam => (
          <button
            key={cam.id}
            onClick={() => onSelect(cam.id)}
            className={`w-full text-left px-4 py-3 flex items-center gap-3
              transition-colors duration-150
              ${selected === cam.id
                ? "bg-blue-50 border-l-4 border-l-blue-500"
                : "hover:bg-gray-50 border-l-4 border-l-transparent"
              }`}
          >
            <span className="text-xl">{cam.icon}</span>
            <div>
              <div className={`text-sm font-medium
                ${selected === cam.id ? "text-blue-700" : "text-gray-700"}`}>
                {cam.name}
              </div>
              <div className="text-xs text-gray-400">{cam.zone} · {cam.id}</div>
            </div>
            {selected === cam.id && (
              <span className="ml-auto w-2 h-2 rounded-full bg-green-500 animate-pulse"/>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}