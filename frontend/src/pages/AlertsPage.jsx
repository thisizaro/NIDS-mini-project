import { useState, useMemo } from "react";
import { useAnalysisHistory } from "../hooks/useAnalysisHistory";
import { ALERT_TYPES, SEVERITY_CONFIG } from "../constants";
import SeverityBadge from "../components/shared/SeverityBadge";
import DataTable from "../components/shared/DataTable";
import RecommendedActions from "../components/results/RecommendedActions";

function deriveAlerts(history) {
  return history.flatMap((analysis) =>
    (analysis.verdict?.alertsTriggered || []).map((alertType) => ({
      id: `${analysis.id}-${alertType}`,
      timestamp: analysis.timestamp,
      type: alertType,
      severity: analysis.verdict?.verdict,
      attackType: analysis.modelFindings?.attack_type || "--",
      analysisId: analysis.id,
      recommendedActions: analysis.verdict?.recommendedActions || [],
      filename: analysis.filename,
    }))
  );
}

export default function AlertsPage() {
  const { history } = useAnalysisHistory();
  const [typeFilter, setTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  const allAlerts = useMemo(() => deriveAlerts(history), [history]);

  const filtered = useMemo(() => {
    return allAlerts.filter((a) => {
      if (typeFilter && a.type !== typeFilter) return false;
      if (severityFilter && a.severity !== severityFilter) return false;
      return true;
    });
  }, [allAlerts, typeFilter, severityFilter]);

  const columns = [
    {
      key: "timestamp",
      label: "Timestamp",
      render: (v) => (
        <span className="tabular-nums text-xs">{new Date(v).toLocaleString()}</span>
      ),
    },
    {
      key: "type",
      label: "Alert Type",
      render: (v) => (
        <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-xs">
          {v}
        </span>
      ),
    },
    {
      key: "severity",
      label: "Severity",
      render: (v) => <SeverityBadge severity={v} />,
    },
    {
      key: "attackType",
      label: "Attack",
    },
    {
      key: "filename",
      label: "Source",
      render: (v) => <span className="text-xs text-slate-500 truncate max-w-32 inline-block">{v || "--"}</span>,
    },
  ];

  const expanded = expandedId ? filtered.find((a) => a.id === expandedId) : null;

  return (
    <div className="space-y-4 max-w-6xl">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="">All Types</option>
          {ALERT_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="">All Severities</option>
          {Object.keys(SEVERITY_CONFIG).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-xs text-slate-500">{filtered.length} alerts</span>
      </div>

      {/* Table */}
      <div className="bg-slate-800/30 border border-slate-700 rounded-lg overflow-hidden">
        <DataTable
          columns={columns}
          data={filtered}
          onRowClick={(row) => setExpandedId(expandedId === row.id ? null : row.id)}
        />
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border border-slate-700 rounded-lg p-4 space-y-3 bg-slate-800/30">
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-500">
              {expanded.type} alert from {expanded.filename} at{" "}
              {new Date(expanded.timestamp).toLocaleString()}
            </div>
            <button
              className="text-xs text-slate-500 hover:text-slate-300"
              onClick={() => setExpandedId(null)}
            >
              Close
            </button>
          </div>
          <RecommendedActions actions={expanded.recommendedActions} />
        </div>
      )}
    </div>
  );
}
