import { useState } from "react";
import { getVerdict } from "../../api/decisionEngine";
import TestPanel from "./TestPanel";

const PRESETS = {
  normal: {
    label: "Normal Traffic",
    findings: {
      status: "normal",
      attack_detected: false,
      confidence: 0.95,
      flow_count: 150,
    },
  },
  dos: {
    label: "DoS Attack",
    findings: {
      status: "abnormal",
      attack_detected: true,
      attack_type: "DoS",
      confidence: 0.85,
      attack_ratio: 0.72,
      flow_count: 500,
      class_distribution: { "DoS": 360, "Normal": 130, "PortScan": 10 },
    },
  },
  brute: {
    label: "Brute Force",
    findings: {
      status: "abnormal",
      attack_detected: true,
      attack_type: "Brute Force",
      confidence: 0.78,
      attack_ratio: 0.35,
      flow_count: 80,
      class_distribution: { "Brute Force": 28, "Normal": 52 },
    },
  },
  portscan: {
    label: "Port Scan",
    findings: {
      status: "abnormal",
      attack_detected: true,
      attack_type: "PortScan",
      confidence: 0.88,
      attack_ratio: 0.60,
      flow_count: 200,
      class_distribution: { "PortScan": 120, "Normal": 75, "DoS": 5 },
    },
  },
};

const SEVERITY_COLORS = {
  LOW: "bg-green-600",
  MEDIUM: "bg-yellow-600",
  HIGH: "bg-orange-600",
  CRITICAL: "bg-red-600",
};

export default function DecisionEngineTest() {
  const [findings, setFindings] = useState(JSON.stringify(PRESETS.dos.findings, null, 2));
  const [zone, setZone] = useState("Internal");
  const [criticality, setCriticality] = useState("Medium");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handlePreset = (key) => {
    setFindings(JSON.stringify(PRESETS[key].findings, null, 2));
    setResult(null);
  };

  const handleTest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const parsed = JSON.parse(findings);
      const data = await getVerdict(parsed, {
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

  return (
    <TestPanel
      title="Decision Engine Service"
      description="Receives model findings and context (network zone, asset criticality), then determines severity level, generates alerts, and recommends actions."
      endpoint="POST /api/v1/decision/verdict"
      port="8002"
    >
      <div className="space-y-4">
        {/* Presets */}
        <div>
          <p className="text-xs text-slate-400 mb-2">Quick-fill presets:</p>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => handlePreset(key)}
                className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded text-xs hover:bg-slate-600"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* JSON Input */}
        <div>
          <label className="block text-sm text-slate-300 mb-1">Model Findings (JSON)</label>
          <textarea
            value={findings}
            onChange={(e) => setFindings(e.target.value)}
            rows={8}
            className="w-full bg-slate-900 text-slate-300 text-xs font-mono p-3 rounded border border-slate-700 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Context */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Network Zone</label>
            <select
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              className="w-full bg-slate-900 text-slate-300 text-sm p-2 rounded border border-slate-700"
            >
              <option value="Internal">Internal</option>
              <option value="DMZ">DMZ</option>
              <option value="External">External</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Asset Criticality</label>
            <select
              value={criticality}
              onChange={(e) => setCriticality(e.target.value)}
              className="w-full bg-slate-900 text-slate-300 text-sm p-2 rounded border border-slate-700"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleTest}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
        >
          {loading ? "Getting Verdict..." : "Get Verdict"}
        </button>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300">{error}</div>
        )}

        {result && (
          <div className="space-y-3">
            {/* Verdict Badge */}
            <div className="flex items-center gap-3">
              <span className={`px-4 py-2 rounded-md text-white font-bold text-lg ${SEVERITY_COLORS[result.verdict] || "bg-slate-600"}`}>
                {result.verdict}
              </span>
              <span className="text-slate-300 text-sm">{result.summary}</span>
            </div>

            {/* Explanation */}
            <div className="bg-slate-900 p-3 rounded">
              <p className="text-xs text-slate-500 mb-1">Explanation</p>
              <p className="text-sm text-slate-300">{result.explanation}</p>
            </div>

            {/* Alerts */}
            {result.alertsTriggered?.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Alerts Triggered:</p>
                <div className="flex gap-2">
                  {result.alertsTriggered.map((alert) => (
                    <span key={alert} className="px-2 py-1 bg-red-900/40 text-red-300 rounded text-xs border border-red-800">
                      {alert}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            {result.recommendedActions?.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1">Recommended Actions:</p>
                <ul className="list-disc list-inside text-sm text-slate-300 space-y-1">
                  {result.recommendedActions.map((action, i) => (
                    <li key={i}>{action}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Raw JSON */}
            <details className="text-xs">
              <summary className="text-slate-500 cursor-pointer hover:text-slate-300">Raw JSON Response</summary>
              <pre className="bg-slate-900 p-3 rounded mt-1 text-slate-400 overflow-x-auto">{JSON.stringify(result, null, 2)}</pre>
            </details>
          </div>
        )}
      </div>
    </TestPanel>
  );
}
