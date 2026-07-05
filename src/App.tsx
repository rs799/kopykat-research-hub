import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppLayout from "./components/layout/AppLayout";
import Overview from "./pages/Overview";
import NicheScanner from "./pages/NicheScanner";
import WalletDiscovery from "./pages/WalletDiscovery";
import Rankings from "./pages/Rankings";
import Alerts from "./pages/Alerts";
import AlertDetail from "./pages/AlertDetail";
import Paper from "./pages/Paper";
import Backtests from "./pages/Backtests";
import Wallets from "./pages/Wallets";
import Health from "./pages/Health";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Overview />} />
            <Route path="/niches" element={<NicheScanner />} />
            <Route path="/discovery" element={<WalletDiscovery />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/alerts/:id" element={<AlertDetail />} />
            <Route path="/paper" element={<Paper />} />
            <Route path="/backtests" element={<Backtests />} />
            <Route path="/wallets" element={<Wallets />} />
            <Route path="/health" element={<Health />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
