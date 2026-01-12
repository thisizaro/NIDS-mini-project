import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HealthProvider } from "./hooks/useServiceHealth";
import { HistoryProvider } from "./hooks/useAnalysisHistory";
import AppShell from "./components/layout/AppShell";
import DashboardPage from "./pages/DashboardPage";
import AnalyzePage from "./pages/AnalyzePage";
import HistoryPage from "./pages/HistoryPage";
import AlertsPage from "./pages/AlertsPage";
import TestingPage from "./pages/TestingPage";

export default function App() {
  return (
    <BrowserRouter>
      <HealthProvider>
        <HistoryProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analyze" element={<AnalyzePage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/test" element={<TestingPage />} />
            </Route>
          </Routes>
        </HistoryProvider>
      </HealthProvider>
    </BrowserRouter>
  );
}
