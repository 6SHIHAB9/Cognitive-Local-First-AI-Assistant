import { Check, Wifi, Cloud, Cpu, Shield } from "lucide-react";

const privacyItems = [
  { icon: Wifi, label: "Runs fully offline" },
  { icon: Cloud, label: "No cloud APIs" },
  { icon: Cpu, label: "Local models only" },
  { icon: Shield, label: "Files never leave device" },
];

const PrivacyChecklist = () => {
  return (
    <div className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Privacy
      </h2>
      
      <ul className="space-y-2.5">
        {privacyItems.map((item, index) => (
          <li key={index} className="flex items-center gap-3 text-sm">
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 ring-1 ring-emerald-500/30">
              <Check className="h-3 w-3 text-emerald-400" />
            </div>
            <item.icon className="h-4 w-4 text-slate-500" />
            <span className="text-slate-300">{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PrivacyChecklist;
