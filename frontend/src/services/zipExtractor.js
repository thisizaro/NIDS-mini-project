import JSZip from "jszip";

export async function extractCsvs(zipBlob) {
  const zip = await JSZip.loadAsync(zipBlob);
  const csvFiles = [];

  for (const [name, file] of Object.entries(zip.files)) {
    if (name.endsWith(".csv") && !file.dir) {
      const blob = await file.async("blob");
      csvFiles.push(new File([blob], name, { type: "text/csv" }));
    }
  }

  return csvFiles;
}
