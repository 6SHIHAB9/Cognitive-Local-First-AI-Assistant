import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { sendMessageStream, syncVault } from "@/lib/backend";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatAreaProps = {
  setVaultStatus?: (status: any) => void;
};

const ChatArea = ({ setVaultStatus }: ChatAreaProps) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userText = input;
    setInput("");
    setLoading(true);
    setStreaming(false);
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    let messageAdded = false;

    try {
      await sendMessageStream(
        userText,
        (token) => {
          if (!messageAdded) {
            messageAdded = true;
            setStreaming(true);
            setMessages((prev) => [...prev, { role: "assistant", content: token }]);
          } else {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: updated[updated.length - 1].content + token,
              };
              return updated;
            });
          }
        },
        (metadata, syncInfo) => {
          if (syncInfo && setVaultStatus) setVaultStatus(syncInfo);
          setStreaming(false);
          setLoading(false);
        }
      );
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        if (updated[updated.length - 1]?.role === "assistant") {
          updated[updated.length - 1] = { role: "assistant", content: "Connection error. Check backend." };
        } else {
          updated.push({ role: "assistant", content: "Connection error. Check backend." });
        }
        return updated;
      });
      setStreaming(false);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#080c10] font-mono relative overflow-hidden">
      {/* Cyber grid background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(0,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,255,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px'
        }} />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#080c10]/80" />
      </div>

      {/* Corner decorations */}
      <div className="absolute top-0 right-0 w-48 h-48 pointer-events-none">
        <div className="absolute top-3 right-3 w-24 h-24 border-t border-r border-cyan-500/20" />
        <div className="absolute top-6 right-6 w-12 h-12 border-t border-r border-cyan-500/10" />
      </div>

      {/* Header */}
      <header className="relative flex-shrink-0 border-b border-cyan-500/15 bg-[#080c10]/95 backdrop-blur-xl px-8 py-4 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-lg animate-pulse" />
              <div className="relative w-10 h-10 rounded-lg border border-cyan-500/40 bg-cyan-500/8 flex items-center justify-center">
                <svg className="w-5 h-5 text-cyan-400" fill="none" strokeWidth="1.5" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white tracking-widest uppercase">
                  Vault<span className="text-cyan-400">AI</span>
                </h1>
                <div className="h-4 w-px bg-cyan-500/30" />
                <span className="text-xs text-cyan-500/80 tracking-widest uppercase">Neural Interface</span>
              </div>
              <p className="text-xs text-slate-400 tracking-wider mt-0.5">PRIVATE · LOCAL · SECURE</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 rounded border border-cyan-500/25 bg-cyan-500/8">
              <div className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400" />
              </div>
              <span className="text-xs font-bold text-cyan-300 tracking-widest uppercase">Online</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded border border-slate-600/40 bg-slate-800/30">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" strokeWidth="2" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
              </svg>
              <span className="text-xs font-bold text-slate-400 tracking-widest uppercase">Offline</span>
            </div>
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-px overflow-hidden">
          <div className="h-px bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent animate-scan-line" />
        </div>
      </header>

      <style>{`
        @keyframes scan-line {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-scan-line { animation: scan-line 3s ease-in-out infinite; }
        @keyframes flicker {
          0%, 100% { opacity: 1; }
          92% { opacity: 1; }
          93% { opacity: 0.7; }
          94% { opacity: 1; }
        }
        .animate-flicker { animation: flicker 5s infinite; }
      `}</style>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6 relative z-10">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-8">
            {/* Central orb */}
            <div className="relative">
              <div className="absolute inset-0 w-32 h-32 rounded-full bg-cyan-500/10 blur-3xl animate-pulse" />
              <div className="relative w-24 h-24 rounded-full border border-cyan-500/25 bg-gradient-to-br from-cyan-500/10 to-transparent flex items-center justify-center">
                <div className="w-16 h-16 rounded-full border border-cyan-400/35 bg-gradient-to-br from-cyan-400/10 to-transparent flex items-center justify-center">
                  <svg className="w-8 h-8 text-cyan-400" fill="none" strokeWidth="1.5" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 2.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                  </svg>
                </div>
              </div>
            </div>

            <div className="text-center space-y-2">
              <h2 className="text-xl font-bold text-white tracking-widest uppercase animate-flicker">
                Vault <span className="text-cyan-400">Ready</span>
              </h2>
              <p className="text-sm text-slate-400 tracking-wider">QUERY YOUR KNOWLEDGE BASE</p>
            </div>


          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                {/* Avatar */}
                <div className="flex-shrink-0 mt-1">
                  {msg.role === "assistant" ? (
                    <div className="relative">
                      <div className="absolute inset-0 bg-cyan-500/20 rounded blur-md" />
                      <div className="relative w-8 h-8 rounded border border-cyan-500/40 bg-cyan-500/8 flex items-center justify-center">
                        <svg className="w-4 h-4 text-cyan-400" fill="none" strokeWidth="2" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                        </svg>
                      </div>
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded border border-slate-600/50 bg-slate-700/50 flex items-center justify-center">
                      <svg className="w-4 h-4 text-slate-400" fill="none" strokeWidth="2" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Bubble */}
                <div className={`relative max-w-[75%] flex flex-col gap-1 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                  <span className={`text-xs tracking-widest uppercase px-1 ${msg.role === "assistant" ? "text-cyan-500" : "text-slate-500"}`}>
                    {msg.role === "assistant" ? "// VAULT.AI" : "// USER"}
                  </span>
                  <div className={`relative rounded px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-slate-800/80 border border-slate-600/50 text-slate-100"
                      : "bg-[#0a1520]/90 border border-cyan-500/25 text-white"
                  }`}>
                    {msg.role === "assistant" && (
                      <>
                        <div className="absolute top-0 left-0 w-2.5 h-2.5 border-t border-l border-cyan-400/60" />
                        <div className="absolute bottom-0 right-0 w-2.5 h-2.5 border-b border-r border-cyan-400/60" />
                      </>
                    )}
                    <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {msg.content}
                      {streaming && i === messages.length - 1 && msg.role === "assistant" && (
                        <span className="inline-block w-1.5 h-4 bg-cyan-400 ml-0.5 animate-pulse align-middle" />
                      )}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {/* Loading */}
            {loading && !streaming && (
              <div className="flex gap-3">
                <div className="relative flex-shrink-0 mt-1">
                  <div className="absolute inset-0 bg-cyan-500/20 rounded blur-md animate-pulse" />
                  <div className="relative w-8 h-8 rounded border border-cyan-500/40 bg-cyan-500/8 flex items-center justify-center">
                    <svg className="w-4 h-4 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                </div>
                <div className="bg-[#0a1520]/90 border border-cyan-500/25 rounded px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-cyan-500 tracking-widest uppercase mr-1">Processing</span>
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="relative flex-shrink-0 border-t border-cyan-500/15 bg-[#080c10]/95 backdrop-blur-xl px-8 py-4 z-10">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/35 to-transparent" />

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-cyan-500 tracking-widest uppercase font-bold">Input Query</span>
              <div className="flex-1 h-px bg-cyan-500/15" />
            </div>
            <div className="relative group">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
                }}
                placeholder="> Query vault..."
                className="min-h-[52px] max-h-[160px] resize-none bg-[#0a1520]/70 border-cyan-500/25 hover:border-cyan-500/40 focus:border-cyan-400/60 rounded text-sm text-white placeholder:text-slate-600 focus:ring-1 focus:ring-cyan-500/25 transition-all font-mono tracking-wide overflow-y-auto px-4 py-3.5"
                rows={1}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
            </div>
          </div>

          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="h-[52px] w-[52px] flex-shrink-0 rounded border border-cyan-500/35 bg-cyan-500/10 hover:bg-cyan-500/20 hover:border-cyan-400/55 disabled:bg-slate-800/30 disabled:border-slate-700/30 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center group"
          >
            {loading ? (
              <svg className="h-4 w-4 animate-spin text-cyan-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <Send className="h-4 w-4 text-cyan-400 group-hover:text-cyan-300 group-disabled:text-slate-600 transition-colors" />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-slate-500 tracking-wider">
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800/60 border border-slate-700/40 text-slate-400 font-mono text-xs">ENTER</kbd>
            {" "}SEND · {" "}
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800/60 border border-slate-700/40 text-slate-400 font-mono text-xs">SHIFT+ENTER</kbd>
            {" "}NEW LINE
          </p>
          {input.length > 0 && (
            <span className="text-xs text-cyan-600 tracking-widest">{input.length} CHARS</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatArea;