import { apiRequest } from "./client";

export async function predictFromFeatures(features, featureNames) {
  const res = await apiRequest("/api/v1/model/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ features, feature_names: featureNames }),
    timeout: 120000,
  });

  return await res.json();
}

export async function predictFromCsv(csvFile) {
  const formData = new FormData();
  formData.append("file", csvFile);

  const res = await apiRequest("/api/v1/model/predict-csv", {
    method: "POST",
    body: formData,
    timeout: 120000,
  });

  return await res.json();
}
