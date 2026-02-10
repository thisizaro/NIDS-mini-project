import { createContext, useContext, useState, useCallback } from "react";

const STORAGE_KEY = "nids_analysis_history";
const HistoryContext = createContext(null);

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

export function HistoryProvider({ children }) {
  const [history, setHistory] = useState(loadHistory);

  const addAnalysis = useCallback((analysis) => {
    setHistory((prev) => {
      const next = [analysis, ...prev];
      saveHistory(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <HistoryContext.Provider value={{ history, addAnalysis, clearHistory }}>
      {children}
    </HistoryContext.Provider>
  );
}

export function useAnalysisHistory() {
  const ctx = useContext(HistoryContext);
  if (!ctx) return { history: [], addAnalysis: () => {}, clearHistory: () => {} };
  return ctx;
}
