import ServiceHealthPanel from "../components/dashboard/ServiceHealthPanel";
import StatsPanel from "../components/dashboard/StatsPanel";
import SeverityBreakdown from "../components/dashboard/SeverityBreakdown";
import AlertSummary from "../components/dashboard/AlertSummary";
import RecentAnalysesTable from "../components/dashboard/RecentAnalysesTable";

export default function DashboardPage() {
  return (
    <div className="space-y-5 max-w-6xl">
      <ServiceHealthPanel />
      <StatsPanel />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SeverityBreakdown />
        <AlertSummary />
      </div>
      <RecentAnalysesTable />
    </div>
  );
}
