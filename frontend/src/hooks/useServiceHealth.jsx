import { createContext, useContext, useState, useEffect, useCallback } from "react";

const HealthContext = createContext(null);

const DEFAULT_SERVICES = {
  preprocessor: { label: "Preprocessor", status: "unknown", port: 8001 },
  decisionEngine: { label: "Decision Engine", status: "unknown", port: 8002 },
  modelService: { label: "Model Service", status: "unknown", port: 8003 },
  cicflowmeter: { label: "CICFlowMeter", status: "unknown", port: 8010 },
};

export function HealthProvider({ children }) {
  const [services, setServices] = useState(DEFAULT_SERVICES);

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/health");
      if (res.ok) {
        const data = await res.json();
        const now = new Date();
        const updated = {};
        for (const [key, defaults] of Object.entries(DEFAULT_SERVICES)) {
          const backend = data.services?.[key] || {};
          updated[key] = {
            ...defaults,
            status: backend.status || "unhealthy",
            lastChecked: now,
            ...(backend.scaler_loaded !== undefined && { scalerLoaded: backend.scaler_loaded }),
            ...(backend.model_loaded !== undefined && { modelLoaded: backend.model_loaded }),
          };
        }
        setServices(updated);
      } else {
        throw new Error("Orchestrator unhealthy");
      }
    } catch {
      // Orchestrator itself is down — mark all as unhealthy
      const now = new Date();
      setServices((prev) => {
        const updated = {};
        for (const [key, svc] of Object.entries(prev)) {
          updated[key] = { ...svc, status: "unhealthy", lastChecked: now };
        }
        return updated;
      });
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <HealthContext.Provider value={{ services, checkHealth }}>
      {children}
    </HealthContext.Provider>
  );
}

export function useServiceHealth() {
  const ctx = useContext(HealthContext);
  if (!ctx) return { services: DEFAULT_SERVICES, checkHealth: () => {} };
  return ctx;
}
