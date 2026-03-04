import { NETWORK_ZONES, ASSET_CRITICALITY } from "../../constants";

export default function ContextConfigurator({ context, onChange, disabled }) {
  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <label className="block text-xs text-slate-400 mb-1">Network Zone</label>
        <select
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          value={context.networkZone}
          onChange={(e) => onChange({ ...context, networkZone: e.target.value })}
          disabled={disabled}
        >
          <option value="">Select zone...</option>
          {NETWORK_ZONES.map((z) => (
            <option key={z.value} value={z.value}>
              {z.label}
            </option>
          ))}
        </select>
      </div>
      <div className="flex-1">
        <label className="block text-xs text-slate-400 mb-1">Asset Criticality</label>
        <select
          className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
          value={context.assetCriticality}
          onChange={(e) => onChange({ ...context, assetCriticality: e.target.value })}
          disabled={disabled}
        >
          <option value="">Select criticality...</option>
          {ASSET_CRITICALITY.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
