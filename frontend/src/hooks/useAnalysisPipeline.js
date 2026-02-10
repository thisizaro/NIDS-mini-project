import { useReducer, useCallback } from "react";
import { PIPELINE_STEPS, STEP_STATUS } from "../constants";
import { runPipeline } from "../services/pipelineRunner";
import { useAnalysisHistory } from "./useAnalysisHistory";
import { v4 as uuidv4 } from "uuid";

const initialSteps = PIPELINE_STEPS.map((s) => ({
  ...s,
  status: STEP_STATUS.PENDING,
  duration: null,
  error: null,
}));

const initialState = {
  status: "idle", // idle | running | complete | error
  steps: initialSteps,
  result: null,
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "START":
      return {
        ...initialState,
        status: "running",
        steps: initialSteps.map((s) => ({ ...s, status: STEP_STATUS.PENDING })),
      };
    case "STEP_UPDATE": {
      const steps = state.steps.map((s) =>
        s.id === action.stepId
          ? { ...s, status: action.status, duration: action.duration ?? s.duration, error: action.error ?? s.error }
          : s
      );
      return { ...state, steps };
    }
    case "COMPLETE":
      return { ...state, status: "complete", result: action.result };
    case "ERROR":
      return { ...state, status: "error", error: action.error };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

export function useAnalysisPipeline() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { addAnalysis } = useAnalysisHistory();

  const run = useCallback(
    async (pcapFile, context) => {
      dispatch({ type: "START" });

      const onStepUpdate = (stepId, status, extra = {}) => {
        dispatch({ type: "STEP_UPDATE", stepId, status, ...extra });
      };

      try {
        const result = await runPipeline(pcapFile, context, onStepUpdate);
        dispatch({ type: "COMPLETE", result });

        // Save to history (metadata only, no raw feature arrays)
        addAnalysis({
          id: uuidv4(),
          timestamp: new Date().toISOString(),
          filename: pcapFile.name,
          context,
          verdict: result.verdictResult,
          modelFindings: result.modelFindings,
          preprocessMeta: {
            row_count: result.preprocessResult.row_count,
            feature_count: result.preprocessResult.feature_count,
          },
        });
      } catch (err) {
        dispatch({ type: "ERROR", error: err.message || "Pipeline failed" });
      }
    },
    [addAnalysis]
  );

  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  return { ...state, run, reset };
}
