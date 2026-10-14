"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Maximize, Minimize, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface PreviewPanelProps {
  projectId: string;
  runId: string | null;
  runStatus: "idle" | "pending" | "running" | "completed" | "failed" | "cancelled";
  onStop: () => void;
  onRestart: () => void;
}

export function PreviewPanel({ projectId, runId, runStatus, onStop, onRestart }: PreviewPanelProps) {
  const [previewStatus, setPreviewStatus] = useState<"stopped" | "starting" | "running" | "failed" | "stopping">("stopped");
  const [previewPort, setPreviewPort] = useState<number | null>(null);
  const [previewFramework, setPreviewFramework] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const pollPreviewStatus = async () => {
    setIsPolling(true);
    try {
      const response = await fetch(`/api/projects/${projectId}/preview/status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ project_id: projectId }),
      });

      if (!response.ok) throw new Error("Failed to fetch preview status");

      const data = await response.json();
      const preview = data.preview;

      if (preview && preview.status) {
        setPreviewStatus(preview.status);
        setPreviewPort(preview.port);
        setPreviewFramework(preview.framework);
        setPreviewUrl(preview.url_path ? `/p/${preview.url_path}` : null);
      }

      // If stopped or failed, stop polling
      if (preview.status === "stopped" || preview.status === "failed") {
        setIsPolling(false);
      }
    } catch (error) {
      console.error("Preview status poll error:", error);
    } finally {
      setIsPolling(false);
    }
  };

  useEffect(() => {
    // Start polling when component mounts and run is active
    if (runStatus === "running" || runStatus === "pending") {
      const interval = setInterval(pollPreviewStatus, 3000);
      pollPreviewStatus();
      return () => clearInterval(interval);
    }
  }, [runStatus, projectId]);

  // Generate preview URL
  const url = previewPort && previewFramework
    ? `http://localhost:${previewPort}`
    : null;

  return (
    <div className="p-4 border-t bg-background">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Live Preview
        </span>
      </div>

      {/* Status and controls */}
      <div className="mt-2 flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Status:{" "}
          </span>
          <span
            className={cn(
              "rounded px-2 py-0.5 text-[10px] font-medium",
              previewStatus === "running" && "bg-emerald-100 text-emerald-600",
              previewStatus === "starting" && "bg-amber-100 text-amber-600",
              previewStatus === "failed" && "bg-red-100 text-red-600",
              previewStatus === "stopped" && "bg-muted text-muted-foreground",
              previewStatus === "stopping" && "bg-blue-100 text-blue-600"
            )}\n
          >
            {previewStatus}
          </span>
        </div>

        {previewPort && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Port: </span>
            <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">{previewPort}</span>
          </div>
        )}

        {previewFramework && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Framework: </span>
            <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">{previewFramework}</span>
          </div>
        )}

        {/* Preview frame */}
        {previewStatus === "running" && previewPort && (
          <div className="mt-2 rounded border" style={{ borderColor: "var(--border)" }}>
            {previewUrl ? (
              <iframe
                ref={iframeRef}
                src={previewUrl}
                className="w-full h-64 rounded-md"
                style={{ border: "none" }}
                title="Live application preview"
                loading="lazy"
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading preview...
              </div>
            )}
            {iframeRef.current && (
              <button
                onClick={() => iframeRef.current?.scrollTo(0, 0)}
                className="mt-1 text-[10px] text-muted-foreground hover:underline"
                title="Scroll to top"
              >
                ✕
              </button>
            )}
          </div>
        )}

        {/* Controls */}
        {runStatus === "running" && (
          <div className="mt-2 flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={onStop}
              disabled={previewStatus !== "running"}
              title="Stop preview"
            >
              <X className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRestart}
              disabled={previewStatus !== "running"}
              title="Restart preview"
            >
              <Loader2 className="h-3 w-3 animate-spin" />
            </Button>
          </div>
        )}

        {runStatus !== "running" && previewStatus === "stopped" && (
          <div className="mt-2 flex gap-1">
            <Button
              variant="primary"
              size="sm"
              onClick={onRestart}
              disabled={previewStatus !== "stopped"}
              title="Start preview"
            >
              Start Preview
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}