import { SEVERITY_CONFIG } from "../../constants";

export default function SeverityBadge({ severity, size = "sm" }) {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.LOW;
  const sizeClasses =
    size === "lg" ? "px-3 py-1.5 text-sm font-bold" : "px-2 py-0.5 text-xs font-semibold";

  return (
    <span
      className={`inline-flex items-center rounded border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {config.label}
    </span>
  );
}
