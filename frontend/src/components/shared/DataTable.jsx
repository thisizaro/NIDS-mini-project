import { useState } from "react";

export default function DataTable({ columns, data, onRowClick, pageSize = 20 }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(0);

  function handleSort(key) {
    if (!key) return;
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(0);
  }

  let sorted = [...data];
  if (sortKey) {
    sorted.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-slate-400 uppercase border-b border-slate-700">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-3 py-2 ${col.sortable !== false ? "cursor-pointer hover:text-slate-200 select-none" : ""}`}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1">{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-slate-500">
                  No data
                </td>
              </tr>
            ) : (
              paged.map((row, i) => (
                <tr
                  key={row.id || i}
                  className={`border-b border-slate-800 ${onRowClick ? "cursor-pointer hover:bg-slate-800/50" : ""}`}
                  onClick={() => onRowClick && onRowClick(row)}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-2">
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-3 py-2 text-xs text-slate-400">
          <span>
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, sorted.length)} of{" "}
            {sorted.length}
          </span>
          <div className="flex gap-1">
            <button
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Prev
            </button>
            <button
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40"
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
