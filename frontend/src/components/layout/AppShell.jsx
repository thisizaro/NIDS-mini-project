import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

const PAGE_TITLES = {
  "/": "Dashboard",
  "/analyze": "Analyze",
  "/history": "History",
  "/alerts": "Alerts",
};

export default function AppShell() {
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || "NIDS";

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={title} />
        <main className="flex-1 p-5 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
