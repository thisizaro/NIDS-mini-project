import { useState } from "react";

export default function FlowDataTable({ preprocessResult }) {
  const [expanded, setExpanded] = useState(false);

  if (!preprocessResult) return null;

  const { feature_names, features, row_count } = preprocessResult;
  const displayRows = expanded ? features : features.slice(0, 20);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Flow Data ({row_count} rows, {feature_names.length} features)
        </h3>
        {features.length > 20 && (
          <button
            className="text-xs text-blue-400 hover:text-blue-300"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Show less" : `Show all ${features.length}`}
          </button>
        )}
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto border border-slate-800 rounded">
        <table className="text-xs tabular-nums">
          <thead className="sticky top-0 bg-slate-900">
            <tr>
              <th className="px-2 py-1 text-left text-slate-500 font-medium">#</th>
              {feature_names.map((name) => (
                <th key={name} className="px-2 py-1 text-left text-slate-500 font-medium whitespace-nowrap">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                <td className="px-2 py-0.5 text-slate-600">{i + 1}</td>
                {row.map((val, j) => (
                  <td key={j} className="px-2 py-0.5 text-slate-300 whitespace-nowrap">
                    {typeof val === "number" ? val.toFixed(4) : val}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
