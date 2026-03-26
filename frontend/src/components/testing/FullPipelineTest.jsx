import { useState } from "react";
import { analyzePipeline } from "../../api/pipeline";
import TestPanel from "./TestPanel";

const SEVERITY_COLORS = {
  LOW: "bg-green-600",
  MEDIUM: "bg-yellow-600",
  HIGH: "bg-orange-600",
  CRITICAL: "bg-red-600",
};

export default function FullPipelineTest() {
  const [file, setFile] = useState(null);
  const [zone, setZone] = useState("Internal");
  const [criticality, setCriticality] = useState("Medium");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTest = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzePipeline(file, {
        networkZone: zone,
        assetCriticality: criticality,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const steps = result?.steps;
  const verdict = result?.verdict;

  return (
    <TestPanel
      title="Full Pipeline"
      description="Runs the complete IDS pipeline end-to-end: PCAP upload -> CICFlowMeter -> Preprocessing -> 2D CNN + OpenMax Inference -> Decision Engine Verdict."
      endpoint="POST /api/v1/pipeline/analyze"
      port="8080 (Orchestrator)"
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-300 mb-1">Upload PCAP File</label>
          <input
            type="file"
            accept=".pcap,.pcapng"
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Network Zone</label>
            <select value={zone} onChange={(e) => setZone(e.target.value)} className="w-full bg-slate-900 text-slate-300 text-sm p-2 rounded border border-slate-700">
              <option value="Internal">Internal</option>
              <option value="DMZ">DMZ</option>
              <option value="External">External</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Asset Criticality</label>
            <select value={criticality} onChange={(e) => setCriticality(e.target.value)} className="w-full bg-slate-900 text-slate-300 text-sm p-2 rounded border border-slate-700">
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleTest}
          disabled={!file || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
        >
          {loading ? "Running Pipeline..." : "Run Complete Pipeline"}
        </button>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300">{error}</div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Final Verdict */}
            {verdict && (
              <div className="flex items-center gap-3 p-4 bg-slate-900 rounded-lg border border-slate-700">
                <span className={`px-4 py-2 rounded-md text-white font-bold text-lg ${SEVERITY_COLORS[verdict.verdict] || "bg-slate-600"}`}>
                  {verdict.verdict}
                </span>
                <div>
                  <p className="text-slate-200 font-medium">{verdict.summary}</p>
                  <p className="text-xs text-slate-400 mt-1">{verdict.explanation}</p>
                </div>
              </div>
            )}

            {/* Pipeline Steps */}
            {steps && (
              <div className="space-y-2">
                <p className="text-sm text-slate-300 font-medium">Pipeline Steps:</p>

                <StepCard title="1. CICFlowMeter" data={steps.cicflowmeter} />
                <StepCard title="2. Preprocessor" data={steps.preprocessor} />
                <StepCard title="3. Model Inference" data={steps.model} />
                <StepCard title="4. Decision Engine" data={steps.verdict} />
              </div>
            )}

            {/* Model Findings */}
            {result.model_findings && (
              <details className="text-xs">
                <summary className="text-slate-500 cursor-pointer hover:text-slate-300">Model Findings (sent to Decision Engine)</summary>
                <pre className="bg-slate-900 p-3 rounded mt-1 text-slate-400 overflow-x-auto">{JSON.stringify(result.model_findings, null, 2)}</pre>
              </details>
            )}

            {/* Class Distribution */}
            {result.predictions?.class_distribution && (
              <details className="text-xs">
                <summary className="text-slate-500 cursor-pointer hover:text-slate-300">Class Distribution</summary>
                <pre className="bg-slate-900 p-3 rounded mt-1 text-slate-400 overflow-x-auto">{JSON.stringify(result.predictions.class_distribution, null, 2)}</pre>
              </details>
            )}

            {/* Full Response */}
            <details className="text-xs">
              <summary className="text-slate-500 cursor-pointer hover:text-slate-300">Full Raw JSON Response</summary>
              <pre className="bg-slate-900 p-3 rounded mt-1 text-slate-400 overflow-x-auto max-h-96">{JSON.stringify(result, null, 2)}</pre>
            </details>
          </div>
        )}
      </div>
    </TestPanel>
  );
}

function StepCard({ title, data }) {
  if (!data) return null;
  return (
    <details className="bg-slate-900/50 rounded border border-slate-700">
      <summary className="px-4 py-2 text-sm text-slate-300 cursor-pointer hover:bg-slate-800/50 flex items-center gap-2">
        <span className="text-green-400">&#10003;</span>
        {title}
      </summary>
      <div className="px-4 py-2 border-t border-slate-700">
        <pre className="text-xs text-slate-400 overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>
      </div>
    </details>
  );
}
