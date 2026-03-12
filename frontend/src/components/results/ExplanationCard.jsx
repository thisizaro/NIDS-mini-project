export default function ExplanationCard({ explanation, modelFindings, verdictResult }) {
  const details = [];

  if (modelFindings) {
    details.push({ label: "Status", value: modelFindings.status });

    // Show inferred attack label from verdict (dynamic), not raw model class
    const inferredAttack = verdictResult?.inferredAttack;
    if (inferredAttack) {
      details.push({ label: "Threat Identified", value: inferredAttack });
    } else if (modelFindings.attack_type) {
      details.push({ label: "Attack Type", value: modelFindings.attack_type });
    }

    details.push({
      label: "Model Confidence",
      value: `${(modelFindings.confidence * 100).toFixed(1)}%`,
    });
    if (modelFindings.attack_ratio != null) {
      details.push({
        label: "Attack Ratio",
        value: `${(modelFindings.attack_ratio * 100).toFixed(1)}% of flows are malicious`,
      });
    }
    details.push({ label: "Flows Analyzed", value: modelFindings.flow_count?.toLocaleString() });
  }

  // Show class distribution if available
  const dist = modelFindings?.class_distribution;

  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
        Technical Details
      </h3>
      <div className="bg-slate-800/50 rounded-lg overflow-hidden">
        {details.map((d, i) => (
          <div
            key={i}
            className={`flex justify-between px-3 py-1.5 text-sm ${
              i % 2 === 0 ? "bg-slate-800/30" : ""
            }`}
          >
            <span className="text-slate-400">{d.label}</span>
            <span className="text-slate-200 font-mono text-xs">{d.value}</span>
          </div>
        ))}
      </div>

      {dist && Object.keys(dist).length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-slate-500 mb-1.5">Flow Classification Breakdown</p>
          <div className="space-y-1">
            {Object.entries(dist)
              .sort(([, a], [, b]) => b - a)
              .map(([cls, count]) => {
                const total = Object.values(dist).reduce((a, b) => a + b, 0);
                const pct = ((count / total) * 100).toFixed(1);
                return (
                  <div key={cls} className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 w-24 shrink-0">{cls}</span>
                    <div className="flex-1 bg-slate-900 rounded-full h-3 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${cls === "Normal" ? "bg-green-600" : "bg-red-500"}`}
                        style={{ width: `${Math.max(pct, 1)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 w-24 text-right font-mono">
                      {count.toLocaleString()} ({pct}%)
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {explanation && (
        <p className="mt-2 text-xs text-slate-500 leading-relaxed">{explanation}</p>
      )}
    </div>
  );
}
