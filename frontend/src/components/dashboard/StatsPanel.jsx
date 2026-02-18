import { useAnalysisHistory } from "../../hooks/useAnalysisHistory";

export default function StatsPanel() {
  const { history } = useAnalysisHistory();

  const now = Date.now();
  const day = 24 * 60 * 60 * 1000;
  const last24h = history.filter((h) => new Date(h.timestamp) > new Date(now - day));

  const total = history.length;
  const threats = history.filter((h) => h.verdict?.verdict !== "LOW").length;
  const criticalToday = last24h.filter((h) => h.verdict?.verdict === "CRITICAL").length;
  const avgConfidence =
    history.length > 0
      ? (
          history.reduce((sum, h) => sum + (h.modelFindings?.confidence || 0), 0) / history.length
        ).toFixed(2)
      : "--";

  const stats = [
    { label: "Total Analyses", value: total },
    { label: "Threats Detected", value: threats },
    { label: "CRITICAL (24h)", value: criticalToday, highlight: criticalToday > 0 },
    { label: "Avg Confidence", value: avgConfidence },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {stats.map((s) => (
        <div key={s.label} className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
          <p className="text-xs text-slate-500">{s.label}</p>
          <p
            className={`text-xl font-bold mt-0.5 ${
              s.highlight ? "text-red-400" : "text-slate-100"
            }`}
          >
            {s.value}
          </p>
        </div>
      ))}
    </div>
  );
}
