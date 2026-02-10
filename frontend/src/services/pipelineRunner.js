import { processPcap } from "../api/cicflowmeter";
import { preprocessCsv } from "../api/preprocessor";
import { predictFromCsv } from "../api/modelService";
import { getVerdict } from "../api/decisionEngine";
import { extractCsvs } from "./zipExtractor";
import { STEP_STATUS } from "../constants";

export async function runPipeline(pcapFile, context, onStepUpdate) {
  let start;

  // Step 1: CICFlowMeter
  start = Date.now();
  onStepUpdate("cicflowmeter", STEP_STATUS.RUNNING);
  let zipBlob;
  try {
    zipBlob = await processPcap(pcapFile);
    onStepUpdate("cicflowmeter", STEP_STATUS.COMPLETE, { duration: (Date.now() - start) / 1000 });
  } catch (err) {
    onStepUpdate("cicflowmeter", STEP_STATUS.ERROR, { error: err.message });
    throw err;
  }

  // Step 2: Extract CSV
  start = Date.now();
  onStepUpdate("extract", STEP_STATUS.RUNNING);
  let csvFiles;
  try {
    csvFiles = await extractCsvs(zipBlob);
    if (csvFiles.length === 0) throw new Error("No CSV files found in ZIP");
    onStepUpdate("extract", STEP_STATUS.COMPLETE, { duration: (Date.now() - start) / 1000 });
  } catch (err) {
    onStepUpdate("extract", STEP_STATUS.ERROR, { error: err.message });
    throw err;
  }

  // Step 3: Preprocess (for display stats)
  start = Date.now();
  onStepUpdate("preprocess", STEP_STATUS.RUNNING);
  let preprocessResult;
  try {
    preprocessResult = await preprocessCsv(csvFiles[0]);
    onStepUpdate("preprocess", STEP_STATUS.COMPLETE, { duration: (Date.now() - start) / 1000 });
  } catch (err) {
    onStepUpdate("preprocess", STEP_STATUS.ERROR, { error: err.message });
    throw err;
  }

  // Step 4: Model Inference — send raw CSV (model has its own scaler)
  start = Date.now();
  onStepUpdate("inference", STEP_STATUS.RUNNING);
  let modelResult;
  let modelFindings;
  try {
    modelResult = await predictFromCsv(csvFiles[0]);
    modelFindings = modelResult.model_findings;
    onStepUpdate("inference", STEP_STATUS.COMPLETE, { duration: (Date.now() - start) / 1000 });
  } catch (err) {
    onStepUpdate("inference", STEP_STATUS.ERROR, { error: err.message });
    throw err;
  }

  // Step 5: Verdict
  start = Date.now();
  onStepUpdate("verdict", STEP_STATUS.RUNNING);
  let verdictResult;
  try {
    verdictResult = await getVerdict(modelFindings, context);
    onStepUpdate("verdict", STEP_STATUS.COMPLETE, { duration: (Date.now() - start) / 1000 });
  } catch (err) {
    onStepUpdate("verdict", STEP_STATUS.ERROR, { error: err.message });
    throw err;
  }

  return { preprocessResult, modelFindings, modelResult, verdictResult };
}
