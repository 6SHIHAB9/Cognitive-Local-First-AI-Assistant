import { Info } from "lucide-react";

const TeachingInfo = () => {
  return (
    <div className="flex-shrink-0 border-t border-b bg-accent/50 px-6 py-3">
      <div className="flex items-start gap-2.5 text-sm text-accent-foreground">
        <Info className="h-4 w-4 flex-shrink-0 mt-0.5 text-primary" />
        <p>
          In teaching or quiz modes, the assistant may ask questions to test
          understanding.
        </p>
      </div>
    </div>
  );
};

export default TeachingInfo;
