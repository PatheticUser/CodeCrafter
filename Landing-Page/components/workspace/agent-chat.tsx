"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Send, Square, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

export interface ChatItem {
  id: string;
  role: "user" | "assistant" | "status";
  content: string;
  error?: boolean;
}

interface AgentChatProps {
  items: ChatItem[];
  runStatus: "idle" | "pending" | "running" | "completed" | "failed" | "cancelled";
  statusLabel: string;
  onCancel: () => void;
  onSubmit: (prompt: string) => void;
  disabled?: boolean;
}

export function AgentChat({
  items,
  runStatus,
  statusLabel,
  onCancel,
  onSubmit,
  disabled,
}: AgentChatProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const active = runStatus === "running" || runStatus === "pending";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items.length, statusLabel]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || active || disabled) return;
    setInput("");
    onSubmit(prompt);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Bot className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Agent</span>
        <span
          className={cn(
            "ml-auto rounded-full px-2 py-0.5 text-[10px] font-medium",
            runStatus === "running" && "bg-blue-500/10 text-blue-600",
            runStatus === "pending" && "bg-muted text-muted-foreground",
            runStatus === "completed" && "bg-emerald-500/10 text-emerald-600",
            runStatus === "failed" && "bg-red-500/10 text-red-600",
            runStatus === "cancelled" && "bg-amber-500/10 text-amber-600",
            runStatus === "idle" && "bg-muted text-muted-foreground"
          )}
        >
          {statusLabel}
        </span>
        {active && (
          <Button variant="ghost" size="sm" className="h-6 gap-1 px-2 text-[11px] text-red-600" onClick={onCancel}>
            <Square className="h-3 w-3" /> Cancel
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1 px-3 py-2">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 pt-10 text-center text-muted-foreground">
            <Bot className="h-8 w-8" />
            <p className="text-sm">Describe what you want built or changed.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {items.map((item) => (
              <div key={item.id}>
                {item.role === "user" && (
                  <div className="flex gap-2">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                      <User className="h-3 w-3" />
                    </div>
                    <div className="rounded-lg rounded-tl-none bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                      {item.content}
                    </div>
                  </div>
                )}
                {item.role === "assistant" && (
                  <div className="flex gap-2">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                      <Bot className="h-3 w-3" />
                    </div>
                    <div
                      className={cn(
                        "rounded-lg rounded-tl-none px-3 py-2 text-sm whitespace-pre-wrap",
                        item.error ? "bg-red-500/10 text-red-700 dark:text-red-400" : "bg-background border"
                      )}
                    >
                      {item.content}
                    </div>
                  </div>
                )}
                {item.role === "status" && (
                  <p className="pl-8 text-[11px] italic text-muted-foreground">{item.content}</p>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>

      <form onSubmit={handleSubmit} className="border-t p-2">
        <div className="flex gap-1.5">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const prompt = input.trim();
                if (prompt && !active && !disabled) {
                  setInput("");
                  onSubmit(prompt);
                }
              }
            }}
            placeholder={active ? "Agent is working…" : "Ask the agent to build something…"}
            className="min-h-16 max-h-40 flex-1 resize-none text-sm"
            disabled={active || disabled}
          />
          <Button
            type="submit"
            size="icon"
            className="h-9 w-9 shrink-0 self-end"
            disabled={active || disabled || !input.trim()}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
