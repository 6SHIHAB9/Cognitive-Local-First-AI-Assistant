import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Index from "./pages/Index";
import NotFound from "./pages/NotFound";

/* =========================
   Backend bridge (GLOBAL)
   ========================= */

const BACKEND_URL = "http://127.0.0.1:8000";

async function post(endpoint: string, body: any) {
  const res = await fetch(`${BACKEND_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function syncVault() {
  return post("/sync", {});
}

export async function sendMessage(message: string, mode: string) {
  if (mode === "Ask") {
    return post("/ask", { question: message });
  }

  if (mode === "Teach me") {
    return post("/teach", { question: message });
  }

  if (mode === "Quiz me") {
    return post("/quiz", { topic: message });
  }

  return null;
}

/* =========================
   App shell
   ========================= */

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

