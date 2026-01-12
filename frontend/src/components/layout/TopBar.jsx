import { useAnalysisHistory } from "../../hooks/useAnalysisHistory";

export default function TopBar({ title }) {
  const { history } = useAnalysisHistory();

  const criticalCount = history.filter(
    (h) =>
      h.verdict?.verdict === "CRITICAL" &&
      new Date(h.timestamp) > new Date(Date.now() - 24 * 60 * 60 * 1000)
  ).length;

  return (
    <header className="h-12 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between px-5 sticky top-0 z-10 backdrop-blur-sm">
      <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
      <div className="flex items-center gap-4 text-xs text-slate-400">
        {criticalCount > 0 && (
          <span className="px-2 py-0.5 rounded bg-red-900/60 text-red-400 font-medium">
            {criticalCount} CRITICAL (24h)
          </span>
        )}
        <span>{new Date().toLocaleTimeString()}</span>
      </div>
    </header>
  );
}
