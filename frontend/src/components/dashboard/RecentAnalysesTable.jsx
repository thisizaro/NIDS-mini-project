import { useAnalysisHistory } from "../../hooks/useAnalysisHistory";
import SeverityBadge from "../shared/SeverityBadge";

export default function RecentAnalysesTable() {
  const { history } = useAnalysisHistory();
  const recent = history.slice(0, 10);

  if (recent.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 text-center text-sm text-slate-500">
        No analyses yet. Go to Analyze to run your first analysis.
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-700">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Recent Analyses
        </h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500 border-b border-slate-700">
            <th className="px-3 py-1.5 text-left">Time</th>
            <th className="px-3 py-1.5 text-left">Verdict</th>
            <th className="px-3 py-1.5 text-left">Attack</th>
            <th className="px-3 py-1.5 text-left">Zone</th>
            <th className="px-3 py-1.5 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((h) => (
            <tr key={h.id} className="border-b border-slate-800 hover:bg-slate-800/50">
              <td className="px-3 py-1.5 text-slate-400 text-xs tabular-nums">
                {new Date(h.timestamp).toLocaleTimeString()}
              </td>
              <td className="px-3 py-1.5">
                <SeverityBadge severity={h.verdict?.verdict} />
              </td>
              <td className="px-3 py-1.5 text-slate-300">
                {h.modelFindings?.attack_type || "--"}
              </td>
              <td className="px-3 py-1.5 text-slate-400 text-xs">
                {h.context?.networkZone || "--"}
              </td>
              <td className="px-3 py-1.5 text-right text-xs text-slate-500">
                {h.verdict?.recommendedActions?.length || 0} actions
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
