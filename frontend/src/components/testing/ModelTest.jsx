import { useState } from "react";
import { predictFromCsv } from "../../api/modelService";
import TestPanel from "./TestPanel";

export default function ModelTest() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTest = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predictFromCsv(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const summary = result?.predictions?.summary;
  const distribution = result?.predictions?.class_distribution;
  const perFlow = result?.predictions?.per_flow;

  return (
    <TestPanel
      title="Model Inference Service"
      description="Runs the 2D CNN + OpenMax model on network flow features. Classifies each flow as Normal, DoS, Brute Force, Botnet, PortScan, Web Attack, or Unknown."
      endpoint="POST /api/v1/model/predict-csv"
      port="8003"
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-300 mb-1">Upload CSV File (CICFlowMeter output)</label>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
        </div>

        <button
          onClick={handleTest}
          disabled={!file || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
        >
          {loading ? "Running Inference..." : "Run Prediction"}
        </button>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300">{error}</div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-4 gap-3">
              <Stat label="Total Flows" value={result.flow_count} />
              <Stat label="Status" value={summary?.status} highlight={summary?.attack_detected} />
              <Stat label="Dominant Class" value={summary?.dominant_class} />
              <Stat label="Avg Confidence" value={(summary?.confidence * 100).toFixed(1) + "%"} />
            </div>

            {/* Class Distribution */}
            {distribution && (
              <div>
                <p className="text-xs text-slate-400 mb-2">Class Distribution:</p>
                <div className="space-y-1.5">
                  {Object.entries(distribution)
                    .sort(([, a], [, b]) => b - a)
                    .map(([cls, count]) => {
                      const pct = ((count / result.flow_count) * 100).toFixed(1);
                      return (
                        <div key={cls} className="flex items-center gap-3">
                          <span className="text-xs text-slate-300 w-24 shrink-0">{cls}</span>
                          <div className="flex-1 bg-slate-900 rounded-full h-5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${cls === "Normal" ? "bg-green-600" : "bg-red-600"}`}
                              style={{ width: `${Math.max(pct, 1)}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400 w-20 text-right">{count} ({pct}%)</span>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}

            {/* Per-Flow Table */}
            {perFlow && perFlow.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Per-Flow Predictions (first 20):</p>
                <div className="bg-slate-900 rounded overflow-x-auto max-h-64">
                  <table className="w-full text-xs text-slate-300">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="p-2 text-left">Flow</th>
                        <th className="p-2 text-left">Prediction</th>
                        <th className="p-2 text-left">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {perFlow.slice(0, 20).map((flow) => (
                        <tr key={flow.flow_id} className="border-b border-slate-800">
                          <td className="p-2 font-mono">#{flow.flow_id}</td>
                          <td className="p-2">
                            <span className={`px-1.5 py-0.5 rounded text-xs ${flow.prediction === "Normal" ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>
                              {flow.prediction}
                            </span>
                          </td>
                          <td className="p-2 font-mono">{(flow.confidence * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </TestPanel>
  );
}

function Stat({ label, value, highlight }) {
  return (
    <div className="bg-slate-900/50 p-3 rounded">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-sm font-medium ${highlight ? "text-red-400" : "text-slate-200"}`}>{String(value)}</p>
    </div>
  );
}
