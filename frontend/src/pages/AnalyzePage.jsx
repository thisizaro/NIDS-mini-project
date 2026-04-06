import { useState } from "react";
import PcapUploader from "../components/analyze/PcapUploader";
import ContextConfigurator from "../components/analyze/ContextConfigurator";
import PipelineProgress from "../components/analyze/PipelineProgress";
import ResultsPanel from "../components/analyze/ResultsPanel";
import { useAnalysisPipeline } from "../hooks/useAnalysisPipeline";

export default function AnalyzePage() {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState({
    networkZone: "Internal",
    assetCriticality: "Low",
  });
  const pipeline = useAnalysisPipeline();

  const canRun = file && pipeline.status !== "running";

  function handleRun() {
    if (!canRun) return;
    pipeline.run(file, {
      networkZone: context.networkZone,
      assetCriticality: context.assetCriticality,
    });
  }

  function handleReset() {
    pipeline.reset();
    setFile(null);
    setContext({ networkZone: "", assetCriticality: "" });
  }

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Upload & Config */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            PCAP File
          </h3>
          <PcapUploader
            file={file}
            onFileSelect={setFile}
            disabled={pipeline.status === "running"}
          />
        </div>
        <div className="flex items-center">
          {/*<h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            Context
          </h3>*/}
          {/*<ContextConfigurator
            context={context}
            onChange={setContext}
            disabled={pipeline.status === "running"}
          />*/}
          <div className="flex gap-2 mt-3">
            <button
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                canRun
                  ? "bg-blue-600 hover:bg-blue-500 text-white"
                  : "bg-slate-800 text-slate-500 cursor-not-allowed"
              }`}
              onClick={handleRun}
              disabled={!canRun}
            >
              {pipeline.status === "running" ? "Running..." : "Run Analysis"}
            </button>
            {(pipeline.status === "complete" ||
              pipeline.status === "error") && (
              <button
                className="px-4 py-2 rounded text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
                onClick={handleReset}
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Progress */}
      {pipeline.status !== "idle" && (
        <div>
          <h3 className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
            Pipeline Progress
          </h3>
          <PipelineProgress steps={pipeline.steps} />
          {pipeline.error && (
            <p className="mt-2 text-sm text-red-400">Error: {pipeline.error}</p>
          )}
        </div>
      )}

      {/* Results */}
      {pipeline.status === "complete" && pipeline.result && (
        <div>
          <h3 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
            Results
          </h3>
          <ResultsPanel result={pipeline.result} />
        </div>
      )}
    </div>
  );
}
