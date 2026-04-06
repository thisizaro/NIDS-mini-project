import { useState, useMemo } from "react";
import { useAnalysisHistory } from "../hooks/useAnalysisHistory";
import { SEVERITY_CONFIG, NETWORK_ZONES } from "../constants";
import SeverityBadge from "../components/shared/SeverityBadge";
import DataTable from "../components/shared/DataTable";
import VerdictBanner from "../components/results/VerdictBanner";
import RecommendedActions from "../components/results/RecommendedActions";
import AlertsTriggered from "../components/results/AlertsTriggered";
import ExplanationCard from "../components/results/ExplanationCard";

export default function HistoryPage() {
  const { history, clearHistory } = useAnalysisHistory();
  const [severityFilter, setSeverityFilter] = useState("");
  const [zoneFilter, setZoneFilter] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const filtered = useMemo(() => {
    return history.filter((h) => {
      if (severityFilter && h.verdict?.verdict !== severityFilter) return false;
      if (zoneFilter && h.context?.networkZone !== zoneFilter) return false;
      return true;
    });
  }, [history, severityFilter, zoneFilter]);

  const columns = [
    {
      key: "timestamp",
      label: "Timestamp",
      render: (v) => (
        <span className="tabular-nums text-xs">{new Date(v).toLocaleString()}</span>
      ),
    },
    {
      key: "verdict",
      label: "Verdict",
      render: (_, row) => <SeverityBadge severity={row.verdict?.verdict} />,
    },
    {
      key: "attack",
      label: "Attack Type",
      render: (_, row) => row.modelFindings?.attack_type || "--",
    },
    //{
    //  key: "zone",
    //  label: "Zone",
    //  render: (_, row) => (
    //    <span className="text-xs">{row.context?.networkZone || "--"}</span>
    //  ),
    //},
    //{
    //  key: "criticality",
    //  label: "Asset",
    //  render: (_, row) => (
    //    <span className="text-xs">{row.context?.assetCriticality || "--"}</span>
    //  ),
    //},
    {
      key: "flows",
      label: "Flows",
      render: (_, row) => (
        <span className="text-xs tabular-nums">
          {row.preprocessMeta?.row_count?.toLocaleString() || "--"}
        </span>
      ),
    },
  ];

  const tableData = filtered.map((h) => ({
    ...h,
    attack: h.modelFindings?.attack_type || "--",
    zone: h.context?.networkZone || "--",
    criticality: h.context?.assetCriticality || "--",
    flows: h.preprocessMeta?.row_count || 0,
  }));

  const expanded = expandedId ? history.find((h) => h.id === expandedId) : null;

  return (
    <div className="space-y-4 max-w-6xl">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        {/*<select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
        >
          <option value="">All Severities</option>
          {Object.keys(SEVERITY_CONFIG).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
          value={zoneFilter}
          onChange={(e) => setZoneFilter(e.target.value)}
        >
          <option value="">All Zones</option>
          {NETWORK_ZONES.map((z) => (
            <option key={z.value} value={z.value}>{z.label}</option>
          ))}
        </select>*/}
        <span className="text-xs text-slate-500">{filtered.length} results</span>
        <div className="ml-auto">
          {showClearConfirm ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Clear all history?</span>
              <button
                className="px-2 py-1 text-xs rounded bg-red-800 text-red-200 hover:bg-red-700"
                onClick={() => {
                  clearHistory();
                  setShowClearConfirm(false);
                }}
              >
                Confirm
              </button>
              <button
                className="px-2 py-1 text-xs rounded bg-slate-800 text-slate-400 hover:bg-slate-700"
                onClick={() => setShowClearConfirm(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            history.length > 0 && (
              <button
                className="px-2 py-1 text-xs rounded bg-slate-800 text-slate-400 hover:bg-slate-700"
                onClick={() => setShowClearConfirm(true)}
              >
                Clear History
              </button>
            )
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-800/30 border border-slate-700 rounded-lg overflow-hidden">
        <DataTable
          columns={columns}
          data={tableData}
          onRowClick={(row) => setExpandedId(expandedId === row.id ? null : row.id)}
        />
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border border-slate-700 rounded-lg p-4 space-y-3 bg-slate-800/30">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Analysis: {expanded.filename} at {new Date(expanded.timestamp).toLocaleString()}
            </span>
            <button
              className="text-xs text-slate-500 hover:text-slate-300"
              onClick={() => setExpandedId(null)}
            >
              Close
            </button>
          </div>
          <VerdictBanner verdict={expanded.verdict} />
          <div className="grid grid-cols-1 lg:grid-cols-1 gap-3">
            {/*<RecommendedActions actions={expanded.verdict?.recommendedActions} />*/}
            <div className="space-y-3">
              {/*<AlertsTriggered alerts={expanded.verdict?.alertsTriggered} />*/}
              <ExplanationCard
                explanation={expanded.verdict?.explanation}
                modelFindings={expanded.modelFindings}
                verdictResult={expanded.verdict}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
