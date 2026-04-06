import VerdictBanner from "../results/VerdictBanner";
import RecommendedActions from "../results/RecommendedActions";
import AlertsTriggered from "../results/AlertsTriggered";
import ExplanationCard from "../results/ExplanationCard";
import FlowDataTable from "../results/FlowDataTable";

export default function ResultsPanel({ result }) {
  if (!result) return null;

  const { verdictResult, modelFindings, preprocessResult } = result;

  return (
    <div className="space-y-4">
      <VerdictBanner verdict={verdictResult} />

      <div className="grid grid-cols-1 lg:grid-cols-1 gap-4">
        {/*<RecommendedActions actions={verdictResult.recommendedActions} />*/}
        <div className="space-y-4">
          {/*<AlertsTriggered alerts={verdictResult.alertsTriggered} />*/}
          <ExplanationCard
            explanation={verdictResult.explanation}
            modelFindings={modelFindings}
            verdictResult={verdictResult}
          />
        </div>
      </div>

      <FlowDataTable preprocessResult={preprocessResult} />
    </div>
  );
}
