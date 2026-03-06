import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { queryClient } from "@/lib/query-client";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import IntakePage from "./pages/IntakePage";
import IntakeDetailPage from "./pages/IntakeDetailPage";
import RFQsPage from "./pages/RFQsPage";
import RFQDetailPage from "./pages/RFQDetailPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import SuppliersPage from "./pages/SuppliersPage";
import ClientsPage from "./pages/ClientsPage";
import ValidationsPage from "./pages/ValidationsPage";
import SettingsPage from "./pages/SettingsPage";
import NotFound from "./pages/NotFound";

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<DashboardPage />} />
          <Route path="/intake" element={<IntakePage />} />
          <Route path="/intake/:id" element={<IntakeDetailPage />} />
          <Route path="/rfqs" element={<RFQsPage />} />
          <Route path="/rfqs/:id" element={<RFQDetailPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/validations" element={<ValidationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
