import { apiRequest } from "./client";

export async function getVerdict(modelFindings, context) {
  const res = await apiRequest("/api/v1/decision/verdict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modelFindings, context }),
    timeout: 30000,
  });

  return await res.json();
}
