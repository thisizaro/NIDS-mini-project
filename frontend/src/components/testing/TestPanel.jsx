export default function TestPanel({ title, description, endpoint, port, children }) {
  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        <p className="text-sm text-slate-400 mt-1">{description}</p>
        <div className="flex gap-4 mt-2">
          <span className="text-xs text-slate-500">
            Endpoint: <code className="text-blue-400">{endpoint}</code>
          </span>
          <span className="text-xs text-slate-500">
            Port: <code className="text-blue-400">{port}</code>
          </span>
        </div>
      </div>
      {children}
    </div>
  );
}
