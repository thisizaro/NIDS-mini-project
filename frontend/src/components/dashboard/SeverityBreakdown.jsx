import { SEVERITY_CONFIG } from "../../constants";
import { useAnalysisHistory } from "../../hooks/useAnalysisHistory";

export default function SeverityBreakdown() {
  const { history } = useAnalysisHistory();

  const counts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
  history.forEach((h) => {
    const sev = h.verdict?.verdict;
    if (sev && counts[sev] !== undefined) counts[sev]++;
  });

  const max = Math.max(...Object.values(counts), 1);

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
      <h3 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
        Severity Breakdown
      </h3>
      <div className="space-y-2">
        {Object.entries(counts).map(([sev, count]) => {
          const config = SEVERITY_CONFIG[sev];
          return (
            <div key={sev} className="flex items-center gap-2">
              <span className={`text-xs w-16 ${config.text}`}>{sev}</span>
              <div className="flex-1 bg-slate-900 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full rounded-full ${config.dot}`}
                  style={{ width: `${(count / max) * 100}%`, minWidth: count > 0 ? "8px" : "0" }}
                />
              </div>
              <span className="text-xs text-slate-400 w-6 text-right tabular-nums">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
