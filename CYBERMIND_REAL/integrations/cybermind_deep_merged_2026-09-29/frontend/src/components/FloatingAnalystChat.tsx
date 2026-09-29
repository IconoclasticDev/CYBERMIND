import React, { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, Loader2, MessageCircle, X } from "lucide-react";
import { api, type AnalystChatReply } from "../lib/api";

type Message = { id: number; role: "assistant" | "user"; text: string; source?: string; scope?: string };
const SUGGESTIONS = [
  "Summarize loaded traffic",
  "Which attack labels are present?",
  "Which hosts are most active?",
  "What does the model forecast?",
];

export const FloatingAnalystChat: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0, role: "assistant",
      text: "Ask me about traffic, attack labels, hosts, ports, provenance, or the current forecast. I answer from this local session only.",
      source: "CYBERMIND data assistant",
    },
  ]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }, [messages, busy]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const send = async (question: string) => {
    const clean = question.trim();
    if (!clean || busy) return;
    setDraft("");
    setMessages((current) => [...current, { id: nextId.current++, role: "user" as const, text: clean }].slice(-30));
    setBusy(true);
    try {
      const reply: AnalystChatReply = await api.askAnalyst(clean);
      setMessages((current) => [...current, {
        id: nextId.current++, role: "assistant" as const, text: reply.answer,
        source: reply.source, scope: reply.scope,
      }].slice(-30));
    } catch (error) {
      setMessages((current) => [...current, {
        id: nextId.current++, role: "assistant" as const,
        text: error instanceof Error ? error.message : "The local assistant is unavailable. Please retry.",
      }].slice(-30));
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[60] flex flex-col items-end gap-3 pointer-events-none">
      {open && (
        <section
          role="dialog" aria-label="CYBERMIND data assistant"
          className="pointer-events-auto w-[min(390px,calc(100vw-2rem))] h-[min(590px,calc(100dvh-7rem))] min-h-[330px] flex flex-col overflow-hidden bg-[#FAF8F5] border border-[#DDD6CC] rounded-2xl shadow-[0_18px_55px_rgba(28,35,43,0.22)]"
        >
          <div className="px-4 py-3.5 bg-white border-b border-[#EAE6DF] flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#FCEAE5] text-[#D75443] flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-editorial text-[17px] font-semibold text-[#1C232B] leading-tight">CYBERMIND Analyst</h2>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[#6B7787]">Offline · domain-trained NLP · read-only</p>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close assistant"
              className="p-2 rounded-lg text-[#6B7787] hover:text-[#1C232B] hover:bg-[#F3F0EB] transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-3" aria-live="polite">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed whitespace-pre-wrap break-words ${
                  message.role === "user"
                    ? "bg-[#DE5B49] text-white rounded-br-md"
                    : "bg-white border border-[#E8E2D9] text-[#28323D] rounded-bl-md shadow-xs"
                }`}>
                  {message.text}
                  {message.source && (
                    <div className="mt-2 pt-2 border-t border-[#EAE6DF] text-[10px] text-[#778391] leading-snug">
                      Source: {message.source}{message.scope ? ` · ${message.scope}` : ""}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="flex items-center gap-2 text-[11px] text-[#6B7787]"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Reading local data…</div>}
          </div>

          {messages.length <= 1 && (
            <div className="px-4 pb-2 flex flex-wrap gap-1.5">
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => void send(suggestion)}
                  className="px-2.5 py-1.5 rounded-lg border border-[#E5DED3] bg-white text-[10px] font-semibold text-[#596676] hover:border-[#DE5B49] hover:text-[#BD4839] transition-colors">
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={(event) => { event.preventDefault(); void send(draft); }} className="p-3 bg-white border-t border-[#EAE6DF]">
            <div className="flex items-end gap-2 bg-[#FAF8F5] border border-[#DDD6CC] rounded-xl pl-3 pr-1.5 py-1.5 focus-within:border-[#DE5B49] transition-colors">
              <textarea ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} rows={1} maxLength={500}
                onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(draft); } }}
                placeholder="Ask about the loaded data…" aria-label="Ask about the loaded data"
                className="flex-1 min-w-0 max-h-20 resize-none bg-transparent text-xs text-[#1C232B] placeholder:text-[#8D98A5] outline-none py-1.5" />
              <button type="submit" disabled={!draft.trim() || busy} aria-label="Send question"
                className="w-8 h-8 shrink-0 rounded-lg bg-[#DE5B49] text-white flex items-center justify-center hover:bg-[#C74E3E] disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[9px] text-[#909AA6] mt-1.5 text-center">Local session answers only. Predictions are not observed facts.</p>
          </form>
        </section>
      )}

      <button type="button" onClick={() => setOpen((current) => !current)}
        aria-label={open ? "Close data assistant" : "Open data assistant"} aria-expanded={open}
        className="pointer-events-auto w-14 h-14 rounded-full bg-[#DE5B49] text-white flex items-center justify-center shadow-[0_8px_25px_rgba(180,65,48,0.35)] ring-4 ring-white hover:bg-[#C74E3E] hover:scale-105 transition-transform">
        {open ? <X className="w-5 h-5" /> : <MessageCircle className="w-6 h-6" />}
      </button>
    </div>
  );
};
