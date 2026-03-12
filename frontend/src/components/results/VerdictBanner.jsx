import { SEVERITY_CONFIG } from "../../constants";

export default function VerdictBanner({ verdict }) {
  if (!verdict) return null;
  const config = SEVERITY_CONFIG[verdict.verdict] || SEVERITY_CONFIG.LOW;

  return (
    <div className={`rounded-lg border-2 ${config.border} ${config.bg} p-4`}>
      <div className="flex items-center gap-3">
        <span className={`text-2xl font-black ${config.text}`}>{verdict.verdict}</span>
        <span className="text-sm text-slate-300">{verdict.summary}</span>
      </div>
    </div>
  );
}
