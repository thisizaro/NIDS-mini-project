import { useState } from "react";
import CicflowmeterTest from "../components/testing/CicflowmeterTest";
import PreprocessorTest from "../components/testing/PreprocessorTest";
import ModelTest from "../components/testing/ModelTest";
import DecisionEngineTest from "../components/testing/DecisionEngineTest";
import FullPipelineTest from "../components/testing/FullPipelineTest";

const TABS = [
  { id: "cicflowmeter", label: "CICFlowMeter", icon: "\u{1F4E1}" },
  { id: "preprocessor", label: "Preprocessor", icon: "\u{1F9F9}" },
  { id: "model", label: "Model Inference", icon: "\u{1F9E0}" },
  { id: "decision", label: "Decision Engine", icon: "\u2696\uFE0F" },
  { id: "pipeline", label: "Full Pipeline", icon: "\u{1F680}" },
];

export default function TestingPage() {
  const [activeTab, setActiveTab] = useState("cicflowmeter");

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Service Testing</h1>
        <p className="text-sm text-slate-400 mt-1">
          Test each pipeline service individually or run the complete pipeline end-to-end.
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 mb-6 bg-slate-800/50 rounded-lg p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
            }`}
          >
            <span>{tab.icon}</span>
            <span className="hidden lg:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-slate-800/30 rounded-lg border border-slate-700 p-6">
        {activeTab === "cicflowmeter" && <CicflowmeterTest />}
        {activeTab === "preprocessor" && <PreprocessorTest />}
        {activeTab === "model" && <ModelTest />}
        {activeTab === "decision" && <DecisionEngineTest />}
        {activeTab === "pipeline" && <FullPipelineTest />}
      </div>
    </div>
  );
}
