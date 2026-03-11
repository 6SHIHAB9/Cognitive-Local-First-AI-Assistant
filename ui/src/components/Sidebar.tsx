import { useState } from "react";
import { syncVault } from "@/lib/backend";

const Sidebar = ({ vaultStatus, setVaultStatus }) => {
  const [syncing, setSyncing] = useState(false);
  const [syncPulse, setSyncPulse] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const data = await syncVault();
      if (setVaultStatus) setVaultStatus(data);
      setSyncPulse(true);
      setTimeout(() => setSyncPulse(false), 1000);
    } catch (e) {
      console.error("Sync failed", e);
    } finally {
      setSyncing(false);
    }
  };

  const formatTime = (ts: number) => {
    if (!ts) return "—";
    return new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  const fileCount = vaultStatus?.indexed_files ?? 0;

  return (
    <aside className="w-72 flex-shrink-0 h-screen overflow-y-auto bg-[#060a0e] border-r border-cyan-500/15 flex flex-col font-mono relative">
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: `linear-gradient(rgba(0,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,255,0.025) 1px, transparent 1px)`,
        backgroundSize: '20px 20px'
      }} />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />

      <div className="relative flex-1 p-5 space-y-5">

        {/* Logo */}
        <div className="flex items-center gap-3 pt-1">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500/20 rounded blur-lg" />
            <div className="relative w-10 h-10 rounded border border-cyan-500/40 bg-cyan-500/8 flex items-center justify-center">
              <svg className="w-5 h-5 text-cyan-400" fill="none" strokeWidth="1.5" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
          </div>
          <div>
            <div className="text-base font-bold text-white tracking-widest uppercase">
              Vault<span className="text-cyan-400">AI</span>
            </div>
            <div className="text-xs text-slate-400 tracking-wider">Private & Offline</div>
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/25 to-transparent" />

        {/* Vault Status */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-px flex-1 bg-cyan-500/15" />
            <span className="text-xs text-cyan-400 tracking-widest uppercase font-bold">Vault Status</span>
            <div className="h-px flex-1 bg-cyan-500/15" />
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Files", value: vaultStatus?.indexed_files ?? "—" },
              { label: "Detected", value: vaultStatus?.file_count ?? "—" },
              { label: "Empty", value: vaultStatus?.empty_files ?? "—" },
              { label: "Status", value: fileCount > 0 ? "OK" : "—" },
            ].map((stat, i) => (
              <div key={i} className="relative rounded border border-cyan-500/15 bg-cyan-500/5 px-3 py-2.5 overflow-hidden hover:border-cyan-500/30 transition-colors">
                <div className="absolute top-0 left-0 w-0.5 h-full bg-cyan-500/40" />
                <div className="text-xs text-slate-400 tracking-wider uppercase mb-1">{stat.label}</div>
                <div className={`text-lg font-bold tracking-wider ${stat.value === "OK" ? "text-cyan-400" : "text-white"}`}>
                  {stat.value}
                </div>
              </div>
            ))}
          </div>

          <div className="rounded border border-cyan-500/15 bg-[#0a1520]/60 px-3 py-2.5">
            <div className="text-xs text-slate-400 tracking-wider uppercase mb-1">Vault Path</div>
            <div className="text-sm text-cyan-300 font-mono truncate">
              {vaultStatus?.vault_path ?? "~/vault/"}
            </div>
          </div>

          {vaultStatus?.last_indexed && (
            <div className="flex items-center justify-between px-1">
              <span className="text-xs text-slate-400 tracking-wider uppercase">Last Sync</span>
              <span className="text-xs text-cyan-300 font-mono">{formatTime(vaultStatus.last_indexed)}</span>
            </div>
          )}

          <button
            onClick={handleSync}
            disabled={syncing}
            className={`relative w-full py-3 rounded border transition-all duration-200 overflow-hidden group ${
              syncing
                ? "border-cyan-500/25 bg-cyan-500/5 cursor-not-allowed"
                : "border-cyan-500/40 bg-cyan-500/8 hover:bg-cyan-500/15 hover:border-cyan-400/60"
            }`}
          >
            {syncing && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/15 to-transparent animate-scan-btn" />}
            {syncPulse && <div className="absolute inset-0 bg-cyan-500/10 animate-ping rounded" />}
            <div className="relative flex items-center justify-center gap-2">
              <svg className={`w-4 h-4 text-cyan-400 ${syncing ? "animate-spin" : ""}`} fill="none" strokeWidth="2" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              <span className="text-sm font-bold text-cyan-300 tracking-widest uppercase">
                {syncing ? "Syncing..." : "Sync Vault"}
              </span>
            </div>
          </button>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/25 to-transparent" />

        {/* Security */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-px flex-1 bg-cyan-500/15" />
            <span className="text-xs text-cyan-400 tracking-widest uppercase font-bold">Security</span>
            <div className="h-px flex-1 bg-cyan-500/15" />
          </div>
          <div className="space-y-1">
            {["Runs fully offline", "No cloud APIs used", "Local models only", "Files never uploaded"].map((label, i) => (
              <div key={i} className="flex items-center gap-3 px-2 py-2 rounded hover:bg-cyan-500/5 transition-all group">
                <div className="w-4 h-4 rounded-full border border-cyan-400/50 bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                </div>
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors">{label}</span>
                <span className="ml-auto text-xs text-cyan-400 font-bold">OK</span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/25 to-transparent" />

        {/* System */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="h-px flex-1 bg-cyan-500/15" />
            <span className="text-xs text-cyan-400 tracking-widest uppercase font-bold">System</span>
            <div className="h-px flex-1 bg-cyan-500/15" />
          </div>
          {[
            { label: "Model", value: "gemma2:2b" },
            { label: "Embeddings", value: "mxbai-large" },
            { label: "Reranker", value: "ms-marco" },
            { label: "Mode", value: "Local RAG" },
          ].map((item, i) => (
            <div key={i} className="flex items-center justify-between px-1 py-0.5">
              <span className="text-xs text-slate-400 tracking-wider uppercase">{item.label}</span>
              <span className="text-xs text-cyan-300 font-mono">{item.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="relative border-t border-cyan-500/15 px-5 py-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500 tracking-wider">v1.0.0</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-xs text-cyan-400 tracking-wider uppercase">Active</span>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes scan-btn {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-scan-btn { animation: scan-btn 1s ease-in-out infinite; }
      `}</style>
    </aside>
  );
};

export default Sidebar;