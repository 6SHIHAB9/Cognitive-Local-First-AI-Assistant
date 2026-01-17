import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { useEffect, useState } from "react";
import { syncVault } from "@/lib/backend";

import Index from "./pages/Index";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

export default function App() {
  const [vaultStatus, setVaultStatus] = useState<any>(null);

  useEffect(() => {
    // ✅ Sync once when app loads
    const initialSync = async () => {
      try {
        const data = await syncVault();
        setVaultStatus(data);
      } catch (err) {
        console.error("Initial vault sync failed", err);
      }
    };

    initialSync();
    
    // ✅ No polling! Backend auto-syncs on each /ask request when vault changes
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route
              path="/"
              element={
                <Index
                  vaultStatus={vaultStatus}
                  setVaultStatus={setVaultStatus}
                />
              }
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
}