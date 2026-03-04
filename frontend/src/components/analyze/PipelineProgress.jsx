import { STEP_STATUS } from "../../constants";

function StepIcon({ status }) {
  switch (status) {
    case STEP_STATUS.COMPLETE:
      return <span className="text-green-400 text-lg">&#10003;</span>;
    case STEP_STATUS.RUNNING:
      return (
        <span className="inline-block h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      );
    case STEP_STATUS.ERROR:
      return <span className="text-red-400 text-lg">&#10007;</span>;
    default:
      return <span className="inline-block h-3 w-3 rounded-full bg-slate-600" />;
  }
}

export default function PipelineProgress({ steps }) {
  return (
    <div className="space-y-1">
      {steps.map((step, i) => (
        <div key={step.id}>
          <div className="flex items-center gap-3 py-2 px-3 rounded bg-slate-800/50">
            <div className="w-6 flex justify-center">
              <StepIcon status={step.status} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200 font-medium">{step.label}</p>
              <p className="text-xs text-slate-500">{step.description}</p>
              {step.error && <p className="text-xs text-red-400 mt-0.5">{step.error}</p>}
            </div>
            {step.duration != null && (
              <span className="text-xs text-slate-500 tabular-nums">{step.duration.toFixed(1)}s</span>
            )}
          </div>
          {i < steps.length - 1 && (
            <div className="flex justify-center">
              <div
                className={`w-px h-3 ${
                  step.status === STEP_STATUS.COMPLETE ? "bg-green-700" : "bg-slate-700"
                }`}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
