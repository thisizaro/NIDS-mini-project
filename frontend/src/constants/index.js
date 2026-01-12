export const SEVERITY = {
  LOW: "LOW",
  MEDIUM: "MEDIUM",
  HIGH: "HIGH",
  CRITICAL: "CRITICAL",
};

export const SEVERITY_CONFIG = {
  LOW: {
    label: "LOW",
    bg: "bg-green-900/40",
    text: "text-green-400",
    border: "border-green-600",
    dot: "bg-green-500",
  },
  MEDIUM: {
    label: "MEDIUM",
    bg: "bg-yellow-900/40",
    text: "text-yellow-400",
    border: "border-yellow-600",
    dot: "bg-yellow-500",
  },
  HIGH: {
    label: "HIGH",
    bg: "bg-orange-900/40",
    text: "text-orange-400",
    border: "border-orange-600",
    dot: "bg-orange-500",
  },
  CRITICAL: {
    label: "CRITICAL",
    bg: "bg-red-900/40",
    text: "text-red-400",
    border: "border-red-600",
    dot: "bg-red-500",
  },
};

export const ALERT_TYPES = ["SOC", "Firewall", "Admin", "SIEM"];

export const NETWORK_ZONES = [
  { value: "Internal", label: "Internal" },
  { value: "DMZ", label: "DMZ" },
  { value: "External", label: "External" },
];

export const ASSET_CRITICALITY = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
];

export const PIPELINE_STEPS = [
  { id: "cicflowmeter", label: "CICFlowMeter", description: "Converting PCAP to flow CSV" },
  { id: "extract", label: "Extract CSV", description: "Extracting CSV from ZIP archive" },
  { id: "preprocess", label: "Preprocess", description: "Cleaning and scaling features" },
  { id: "inference", label: "Model Inference", description: "Running 2D CNN + OpenMax classification" },
  { id: "verdict", label: "Decision Engine", description: "Generating security verdict" },
];

export const STEP_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETE: "complete",
  ERROR: "error",
};
