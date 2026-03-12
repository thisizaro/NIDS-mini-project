export default function RecommendedActions({ actions }) {
  if (!actions || actions.length === 0) return null;

  return (
    <div className="border-2 border-amber-700/50 bg-amber-950/20 rounded-lg p-4">
      <h3 className="text-sm font-bold text-amber-400 mb-2 uppercase tracking-wider">
        Recommended Actions
      </h3>
      <ul className="space-y-1.5">
        {actions.map((action, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-200">
            <span className="text-amber-500 mt-0.5 shrink-0">&#9679;</span>
            {action}
          </li>
        ))}
      </ul>
    </div>
  );
}
