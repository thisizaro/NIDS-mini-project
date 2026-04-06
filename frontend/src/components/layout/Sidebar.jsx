import { NavLink } from "react-router-dom";
import StatusDot from "../shared/StatusDot";
import { useServiceHealth } from "../../hooks/useServiceHealth";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "\u25A6" },
  { to: "/analyze", label: "Analyze", icon: "\u25B6" },
  { to: "/history", label: "History", icon: "\u25F0" },
  //{ to: "/alerts", label: "Alerts", icon: "\u26A0" },
  //{ to: "/test", label: "Service Testing", icon: "\u2692" },
];

export default function Sidebar() {
  const { services } = useServiceHealth();

  return (
    <aside className="w-56 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      <div className="px-4 py-4 border-b border-slate-800">
        <h1 className="text-base font-bold text-slate-100 tracking-wide">
          DL Based NIDS
        </h1>
        {/*<p className="text-xs text-slate-500">Intrusion Detection System</p>*/}
      </div>

      <nav className="flex-1 py-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-4 py-2 text-sm ${
                isActive
                  ? "text-white bg-slate-800 border-r-2 border-blue-500"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">
          Services
        </p>
        <div className="space-y-1.5">
          {Object.entries(services).map(([name, svc]) => (
            <div
              key={name}
              className="flex items-center gap-2 text-xs text-slate-400"
            >
              <StatusDot status={svc.status} />
              <span className="truncate">{svc.label}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
