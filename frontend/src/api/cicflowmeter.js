import { apiRequest } from "./client";

export async function processPcap(pcapFile) {
  const formData = new FormData();
  formData.append("file", pcapFile);

  const res = await apiRequest("/api/v1/cicflowmeter/process", {
    method: "POST",
    body: formData,
    timeout: 120000,
  });

  return await res.blob();
}
