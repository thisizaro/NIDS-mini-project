import { apiRequest } from "./client";

export async function preprocessCsv(csvFile) {
  const formData = new FormData();
  formData.append("file", csvFile);

  const res = await apiRequest("/api/v1/preprocessor/preprocess", {
    method: "POST",
    body: formData,
    timeout: 60000,
  });

  return await res.json();
}
