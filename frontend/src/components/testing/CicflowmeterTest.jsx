import { useState } from "react";
import { processPcap } from "../../api/cicflowmeter";
import { extractCsvs } from "../../services/zipExtractor";
import TestPanel from "./TestPanel";

export default function CicflowmeterTest() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTest = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const zipBlob = await processPcap(file);
      const csvFiles = await extractCsvs(zipBlob);

      // Read first few lines of first CSV
      let preview = "";
      if (csvFiles.length > 0) {
        const text = await csvFiles[0].text();
        const lines = text.split("\n");
        preview = lines.slice(0, 6).join("\n");
      }

      setResult({
        zipSize: (zipBlob.size / 1024).toFixed(1) + " KB",
        csvCount: csvFiles.length,
        csvNames: csvFiles.map((f) => f.name),
        preview,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <TestPanel
      title="CICFlowMeter Service"
      description="Converts PCAP network capture files into CSV flow features (85 columns). This is the first step in the pipeline."
      endpoint="POST /api/v1/cicflowmeter/process"
      port="8000"
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-slate-300 mb-1">Upload PCAP File</label>
          <input
            type="file"
            accept=".pcap,.pcapng"
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:bg-blue-600 file:text-white hover:file:bg-blue-700"
          />
        </div>

        <button
          onClick={handleTest}
          disabled={!file || loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
        >
          {loading ? "Processing..." : "Process PCAP"}
        </button>

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-md text-sm text-red-300">{error}</div>
        )}

        {result && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="ZIP Size" value={result.zipSize} />
              <Stat label="CSV Files" value={result.csvCount} />
              <Stat label="File Names" value={result.csvNames.join(", ")} />
            </div>
            {result.preview && (
              <div>
                <p className="text-xs text-slate-400 mb-1">CSV Preview (first 5 rows):</p>
                <pre className="bg-slate-900 p-3 rounded text-xs text-slate-300 overflow-x-auto max-h-48">{result.preview}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </TestPanel>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-slate-900/50 p-3 rounded">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-sm text-slate-200 font-medium truncate">{String(value)}</p>
    </div>
  );
}
