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
    let isMounted = true;

    const sync = async () => {
      try {
        const data = await syncVault();
        if (isMounted) {
          setVaultStatus(data);
        }
      } catch (err) {
        console.error("Vault polling sync failed", err);
      }
    };

    // 🔥 initial sync
    sync();

    // 🔁 poll every 3 seconds
    const interval = setInterval(sync, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
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
