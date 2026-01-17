import { useState } from "react";
import { FolderOpen, RefreshCw, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { syncVault } from "@/lib/backend";

const VaultStatus = ({ vaultStatus, setVaultStatus }) => {
  const [loading, setLoading] = useState(false);

  const handleSync = async () => {
    try {
      setLoading(true);
      const data = await syncVault();
      setVaultStatus(data); // 🔥 update GLOBAL state
    } catch (err) {
      console.error("Vault sync failed", err);
    } finally {
      setLoading(false);
    }
  };

  const fileCount = vaultStatus?.file_count ?? "—";
  const indexedFiles = vaultStatus?.indexed_files ?? "—";
  const emptyFiles = vaultStatus?.empty_files ?? "—";
  const lastIndexed = vaultStatus?.last_indexed;

  return (
    <div className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Vault Status
      </h2>

      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-2.5">
          <FolderOpen className="h-4 w-4 text-primary" />
          <span className="text-slate-400">Vault path:</span>
          <code className="font-mono text-xs bg-slate-800/50 text-primary px-2 py-0.5 rounded-md border border-slate-700">
            ~/vault/
          </code>
        </div>

        <div className="flex items-center gap-2.5">
          <FileText className="h-4 w-4 text-primary" />
          <span className="text-slate-400">Files detected:</span>
          <span className="font-semibold text-white">{fileCount}</span>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-slate-400">Indexed files:</span>
          <span className="text-white">{indexedFiles}</span>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-slate-400">Empty files:</span>
          <span className="text-slate-500">{emptyFiles}</span>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-slate-400">Last indexed:</span>
          <span className="text-slate-500">
            {lastIndexed
              ? new Date(lastIndexed * 1000).toLocaleString()
              : "—"}
          </span>
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        className="w-full gap-2 bg-slate-800/50 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-primary/50"
        onClick={handleSync}
        disabled={loading}
      >
        <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Syncing…" : "Sync Vault"}
      </Button>

      <p className="text-xs text-slate-500 leading-relaxed">
        Files are read locally. Nothing is uploaded.
      </p>
    </div>
  );
};

export default VaultStatus;
