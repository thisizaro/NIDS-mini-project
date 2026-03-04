import { useState, useRef } from "react";

export default function PcapUploader({ file, onFileSelect, disabled }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith(".pcap")) onFileSelect(f);
  }

  function handleChange(e) {
    const f = e.target.files[0];
    if (f) onFileSelect(f);
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
        dragOver ? "border-blue-500 bg-blue-900/20" : "border-slate-700 hover:border-slate-500"
      } ${disabled ? "opacity-50 pointer-events-none" : "cursor-pointer"}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pcap"
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      {file ? (
        <div>
          <p className="text-sm text-slate-200 font-medium">{file.name}</p>
          <p className="text-xs text-slate-500 mt-1">
            {(file.size / 1024).toFixed(1)} KB
          </p>
        </div>
      ) : (
        <div>
          <p className="text-sm text-slate-400">Drop .pcap file here or click to browse</p>
          <p className="text-xs text-slate-600 mt-1">Accepts .pcap files only</p>
        </div>
      )}
    </div>
  );
}
