"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, CircleDashed, Loader2, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ExecutionEntry {
  id: string;
  kind: "tool" | "output" | "error" | "status";
  title: string;
  detail?: string;
  pending?: boolean;
}

interface ExecutionPanelProps {
  entries: ExecutionEntry[];
  className?: string;
}

export function ExecutionPanel({ entries, className }: ExecutionPanelProps) {
  const [expanded, setExpanded] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current && expanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries.length, autoScroll, expanded]);

  return (
    <div className={cn("flex flex-col border-t bg-background", className)}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-2 px-3 py-1.5 text-left"
      >
        <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Execution
        </span>
        {entries.some((e) => e.pending) && (
          <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
        )}
        <span className="ml-1 rounded bg-muted px-1.5 text-[10px] text-muted-foreground">{entries.length}</span>
        {expanded ? (
          <ChevronDown className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronUp className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div
          ref={scrollRef}
          onScroll={(e) => {
            const el = e.currentTarget;
            setAutoScroll(el.scrollHeight - el.scrollTop - el.clientHeight < 24);
          }}
          className="max-h-48 min-h-16 flex-1 overflow-y-auto px-3 pb-2 font-mono text-[11px] leading-relaxed"
        >
          {entries.length === 0 ? (
            <p className="py-3 font-sans text-xs text-muted-foreground">
              Tool calls and command output will appear here.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {entries.map((entry) => (
                <div key={entry.id}>
                  <div
                    className={cn(
                      "flex items-start gap-1.5",
                      entry.kind === "error" && "text-red-600 dark:text-red-400",
                      entry.kind === "status" && "text-muted-foreground"
                    )}
                  >
                    {entry.pending ? (
                      <Loader2 className="mt-0.5 h-3 w-3 shrink-0 animate-spin text-blue-500" />
                    ) : (
                      <CircleDashed className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/60" />
                    )}
                    <span className="font-semibold">{entry.title}</span>
                  </div>
                  {entry.detail && (
                    <pre className="whitespace-pre-wrap break-words pl-5 text-muted-foreground">
                      {entry.detail}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
