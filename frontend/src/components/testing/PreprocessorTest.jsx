import { useState } from "react";
import { preprocessCsv } from "../../api/preprocessor";
import TestPanel from "./TestPanel";

export default function PreprocessorTest() {
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
      const data = await preprocessCsv(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <TestPanel
      title="Preprocessor Service"
      description="Accepts CICFlowMeter CSV output, selects relevant features, cleans data, and applies Z-score normalization. Returns scaled feature vectors ready for model inference."
      endpoint="POST /api/v1/preprocessor/preprocess"
      port="8001"
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
          {loading ? "Preprocessing..." : "Preprocess"}
        </button>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300">{error}</div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Rows" value={result.row_count} />
              <Stat label="Features" value={result.feature_count} />
              <Stat label="Labels" value={result.labels ? "Present" : "None"} />
            </div>

            {result.feature_names && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Feature Names ({result.feature_names.length}):</p>
                <div className="bg-slate-900 p-3 rounded max-h-32 overflow-y-auto">
                  <div className="flex flex-wrap gap-1">
                    {result.feature_names.map((name, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-slate-800 rounded text-xs text-slate-400">{name}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {result.features && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Scaled Features (first 3 rows):</p>
                <div className="bg-slate-900 p-3 rounded overflow-x-auto max-h-48">
                  <table className="text-xs text-slate-300">
                    <tbody>
                      {result.features.slice(0, 3).map((row, i) => (
                        <tr key={i}>
                          <td className="pr-2 text-slate-500 font-mono">[{i}]</td>
                          <td className="font-mono">{row.slice(0, 10).map((v) => v.toFixed(4)).join(", ")}{row.length > 10 ? ", ..." : ""}</td>
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

function Stat({ label, value }) {
  return (
    <div className="bg-slate-900/50 p-3 rounded">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm text-slate-200 font-medium">{String(value)}</p>
    </div>
  );
}
