import { ALERT_TYPES } from "../../constants";
import { useAnalysisHistory } from "../../hooks/useAnalysisHistory";

export default function AlertSummary() {
  const { history } = useAnalysisHistory();

  const counts = {};
  ALERT_TYPES.forEach((t) => (counts[t] = 0));
  history.forEach((h) => {
    (h.verdict?.alertsTriggered || []).forEach((a) => {
      if (counts[a] !== undefined) counts[a]++;
    });
  });

  const max = Math.max(...Object.values(counts), 1);

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
      <h3 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
        Alert Summary
      </h3>
      <div className="space-y-2">
        {ALERT_TYPES.map((type) => (
          <div key={type} className="flex items-center gap-2">
            <span className="text-xs w-16 text-slate-300">{type}</span>
            <div className="flex-1 bg-slate-900 rounded-full h-4 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500"
                style={{ width: `${(counts[type] / max) * 100}%`, minWidth: counts[type] > 0 ? "8px" : "0" }}
              />
            </div>
            <span className="text-xs text-slate-400 w-6 text-right tabular-nums">{counts[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
