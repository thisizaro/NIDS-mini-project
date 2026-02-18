import StatusDot from "../shared/StatusDot";
import { useServiceHealth } from "../../hooks/useServiceHealth";

export default function ServiceHealthPanel() {
  const { services } = useServiceHealth();

  return (
    <div className="grid grid-cols-3 gap-3">
      {Object.entries(services).map(([key, svc]) => (
        <div key={key} className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <StatusDot status={svc.status} />
            <span className="text-sm font-medium text-slate-200">{svc.label}</span>
          </div>
          <div className="text-xs text-slate-500">
            <span>Port {svc.port}</span>
            {key === "preprocessor" && svc.scalerLoaded !== undefined && (
              <span className="ml-2">
                Scaler: {svc.scalerLoaded ? "\u2713" : "\u2717"}
              </span>
            )}
          </div>
          <div className="text-xs text-slate-600 mt-1">
            {svc.status === "healthy" ? "Operational" : svc.status === "unhealthy" ? "Down" : "Checking..."}
          </div>
        </div>
      ))}
    </div>
  );
}
