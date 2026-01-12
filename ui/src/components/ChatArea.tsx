import { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import ChatMessage from "./ChatMessage";
import ModeSelector from "./ModeSelector";
import TeachingInfo from "./TeachingInfo";

const placeholderMessages = [
  {
    role: "user" as const,
    content: "Can you summarize the notes I took on distributed systems?",
  },
  {
    role: "assistant" as const,
    content:
      "Based on your vault notes, distributed systems involve multiple computers working together to appear as a single system. Key concepts include: consistency (all nodes see the same data), availability (system remains operational), and partition tolerance (system continues despite network failures). The CAP theorem states you can only guarantee two of these three properties simultaneously.",
  },
];

const ChatArea = () => {
  const [message, setMessage] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header with Mode Selector */}
      <header className="flex-shrink-0 border-b bg-card/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Assistant</h2>
            <p className="text-xs text-muted-foreground">Ask questions about your vault files</p>
          </div>
        </div>
        <ModeSelector />
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
        {placeholderMessages.map((msg, index) => (
          <ChatMessage key={index} role={msg.role} content={msg.content} />
        ))}
      </div>

      {/* Teaching Info */}
      <TeachingInfo />

      {/* Input Area */}
      <form
        onSubmit={handleSubmit}
        className="flex-shrink-0 border-t bg-card/80 backdrop-blur-sm p-4"
      >
        <div className="flex gap-3">
          <Textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask about your vault files..."
            className="min-h-[48px] max-h-32 resize-none bg-background border-border focus:ring-2 focus:ring-primary/20 focus:border-primary"
            rows={1}
          />
          <Button 
            type="submit" 
            size="icon" 
            className="h-12 w-12 flex-shrink-0 btn-gradient glow-primary rounded-xl"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ChatArea;
