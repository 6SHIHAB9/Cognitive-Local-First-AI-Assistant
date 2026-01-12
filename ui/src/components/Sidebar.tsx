import { Bot } from "lucide-react";
import VaultStatus from "./VaultStatus";
import PrivacyChecklist from "./PrivacyChecklist";

const Sidebar = () => {
  return (
    <aside className="w-80 flex-shrink-0 sidebar-gradient h-screen overflow-y-auto border-r border-white/10">
      <div className="p-5 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl btn-gradient glow-primary">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-white">Local Assistant</h1>
            <p className="text-xs text-slate-400">Private & Offline</p>
          </div>
        </div>
        
        <div className="h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
        
        {/* Vault Status */}
        <VaultStatus />
        
        <div className="h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
        
        {/* Privacy Checklist */}
        <PrivacyChecklist />
      </div>
    </aside>
  );
};

export default Sidebar;
