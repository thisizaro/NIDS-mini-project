const ALERT_ICONS = {
  SOC: "\uD83D\uDC41",
  Firewall: "\uD83D\uDEE1",
  Admin: "\uD83D\uDC64",
  SIEM: "\uD83D\uDCCA",
};

export default function AlertsTriggered({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="text-xs text-slate-500">No alerts triggered</div>
    );
  }

  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
        Alerts Triggered
      </h3>
      <div className="flex flex-wrap gap-2">
        {alerts.map((alert) => (
          <span
            key={alert}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-200"
          >
            <span>{ALERT_ICONS[alert] || "\u26A0"}</span>
            {alert}
          </span>
        ))}
      </div>
    </div>
  );
}
