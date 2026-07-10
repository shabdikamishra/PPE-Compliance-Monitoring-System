import { useState } from "react";
import StatsBar       from "./components/StatsBar";
import LiveFeed       from "./components/LiveFeed";
import ViolationLog   from "./components/ViolationLog";
import CameraSelector from "./components/CameraSelector";
import AnalyticsPanel from "./components/AnalyticsPanel";

export default function App() {
  const [selectedCam, setSelectedCam] = useState("CAM_01");

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 text-white rounded-lg p-2 text-lg">🦺</div>
            <div>
              <h1 className="text-base font-semibold text-gray-900">
                PPE Compliance Monitor
              </h1>
              <p className="text-xs text-gray-400">
                AI-powered real-time safety monitoring
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-green-50 border border-green-200
              rounded-full px-3 py-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"/>
            <span className="text-xs font-medium text-green-700">System Live</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-5 space-y-4">
        {/* Stats row */}
        <StatsBar />

        {/* Three-column main layout */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-2">
            <CameraSelector selected={selectedCam} onSelect={setSelectedCam} />
          </div>
          <div className="col-span-5">
            <LiveFeed cameraId={selectedCam} />
          </div>
          <div className="col-span-5">
            <ViolationLog />
          </div>
        </div>

        {/* Analytics row — full width below */}
        <AnalyticsPanel />
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-4">
        <div className="text-xs text-gray-400 text-center">
          PPE Compliance Monitor · YOLOv8 · FastAPI · React · PostgreSQL
        </div>
      </footer>
    </div>
  );
}