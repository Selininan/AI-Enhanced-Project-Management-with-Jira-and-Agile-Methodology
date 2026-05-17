import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { supportAsk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, Send, MessageSquarePlus } from "lucide-react";
import { TypingDots } from "@/components/shared";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

interface Msg { role: "user" | "ai"; content: string }

const SUGGESTIONS = [
  "Which tasks are delayed?",
  "Is the sprint overloaded?",
  "Who has the most risk?",
];

const HISTORY = [
  "Sprint 4 retrospective",
  "Risk score deep dive",
  "Capacity planning Q&A",
  "BRD gap discussion",
];

function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || loading) return;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);
    const answer = await supportAsk(q);
    setMessages((m) => [...m, { role: "ai", content: answer }]);
    setLoading(false);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <aside className="hidden md:flex w-64 flex-col border-r border-border bg-muted/30">
        <div className="p-3 border-b border-border">
          <Button
            variant="outline"
            className="w-full justify-start"
            onClick={() => setMessages([])}
          >
            <MessageSquarePlus className="h-4 w-4 mr-2" />
            New chat
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
            Recent
          </div>
          {HISTORY.map((h, i) => (
            <button
              key={i}
              className="w-full text-left rounded-md px-2.5 py-2 text-sm hover:bg-accent text-foreground/80 truncate"
            >
              {h}
            </button>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 bg-background">
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6">
          <div className="max-w-3xl mx-auto space-y-5">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 text-primary grid place-items-center mb-3">
                  <Bot className="h-6 w-6" />
                </div>
                <h2 className="text-lg font-semibold">AI Sprint Assistant</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Ask anything about your sprint, risks, or capacity.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-full border border-border bg-card px-3.5 py-1.5 text-xs hover:bg-accent transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                className={cn(
                  "flex gap-3",
                  m.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {m.role === "ai" && (
                  <div className="h-7 w-7 rounded-full bg-primary/10 text-primary grid place-items-center shrink-0">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div
                  className={cn(
                    "rounded-2xl px-4 py-2.5 text-sm max-w-[80%] whitespace-pre-wrap",
                    m.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-muted text-foreground rounded-bl-sm"
                  )}
                >
                  {m.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start">
                <div className="h-7 w-7 rounded-full bg-primary/10 text-primary grid place-items-center shrink-0">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-3">
                  <TypingDots />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="border-t border-border bg-background px-4 md:px-8 py-3">
          <form
            className="max-w-3xl mx-auto flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about your sprint..."
              className="flex-1"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}