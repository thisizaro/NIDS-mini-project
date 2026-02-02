import { apiRequest } from "./client";

export async function analyzePipeline(pcapFile, context) {
  const formData = new FormData();
  formData.append("file", pcapFile);
  formData.append("context", JSON.stringify(context));

  const res = await apiRequest("/api/v1/pipeline/analyze", {
    method: "POST",
    body: formData,
    timeout: 300000,
  });

  return await res.json();
}
