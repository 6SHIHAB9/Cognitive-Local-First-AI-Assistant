import { useState } from "react";
import { MessageSquare, FileText, Lightbulb, GraduationCap, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const modes = [
  { id: "ask", label: "Ask", icon: MessageSquare },
  { id: "summarize", label: "Summarize", icon: FileText },
  { id: "explain", label: "Explain", icon: Lightbulb },
  { id: "teach", label: "Teach me", icon: GraduationCap },
  { id: "quiz", label: "Quiz me", icon: HelpCircle },
];

const ModeSelector = () => {
  const [activeMode, setActiveMode] = useState("ask");

  return (
    <div className="flex flex-wrap gap-2">
      {modes.map((mode) => (
        <button
          key={mode.id}
          onClick={() => setActiveMode(mode.id)}
          className={cn(
            "flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200",
            activeMode === mode.id
              ? "btn-gradient text-white glow-primary"
              : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          )}
        >
          <mode.icon className="h-4 w-4" />
          {mode.label}
        </button>
      ))}
    </div>
  );
};

export default ModeSelector;
