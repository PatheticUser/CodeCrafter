"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, RefreshCw } from "lucide-react";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { FileExplorer, type FileChangeKind } from "@/components/workspace/file-explorer";
import { CodeEditor, type EditorTab } from "@/components/workspace/code-editor";
import { AgentChat, type ChatItem } from "@/components/workspace/agent-chat";
import { ExecutionPanel, type ExecutionEntry } from "@/components/workspace/execution-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { api, ApiError, type AgentEvent, type FileMeta, type Project } from "@/lib/codecrafter";
import { useRunEvents, isTerminal } from "@/lib/run-stream";

type RunStatus = "idle" | "pending" | "running" | "completed" | "failed" | "cancelled";

let idCounter = 0;
const nextId = () => `${Date.now()}-${idCounter++}`;

export default function ProjectEnvironment() {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [files, setFiles] = useState<FileMeta[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [changes, setChanges] = useState<Map<string, FileChangeKind>>(new Map());

  const [tabs, setTabs] = useState<EditorTab[]>([]);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [execEntries, setExecEntries] = useState<ExecutionEntry[]>([]);
  const [runStatus, setRunStatus] = useState<RunStatus>("idle");
  const [statusLabel, setStatusLabel] = useState("Ready");

  const [runId, setRunId] = useState<string | null>(null);
  const [previewStatus, setPreviewStatus] = useState<"stopped" | "starting" | "running" | "failed" | "stopping>("stopped");
  const [previewPort, setPreviewPort] = useState<number | null>(null);
  const [previewFramework, setPreviewFramework] = useState<string | null>(null);

  const runIdRef = useRef<string | null>(null);
  runIdRef.current = runId;

  // ── Initial load ────────────────────────────────────────────────────────────
  const refreshFiles = useCallback(async () => {
    setFilesLoading(true);
    try {
      const { files } = await api.listFiles(projectId);
      setFiles(files);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to list files");
    } finally {
      setFilesLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const proj = await api.getProject(projectId);
        if (cancelled) return;
        setProject(proj);
        // Prefer the auto-seeded session; otherwise create one.
        const sessions = await api.listSessions(projectId);
        if (cancelled) return;
        const existing = sessions[0];
        const sid = existing?.id ?? (await api.createSession(projectId, "Session 1")).id;
        if (cancelled) return;
        setSessionId(sid);
        const { messages } = await api.getMessages(sid);
        if (cancelled) return;
        setChatItems(
          messages.map((m) => ({
            id: m.id,
            role: m.role as ChatItem["role"],
            content: m.content,
          }))
        );

        // Reconnect stream for the last active run (survives page refresh).
        const lastRun = typeof window !== "undefined" ? window.sessionStorage.getItem(`cc_last_run_${projectId}`) : null;
        if (lastRun) {
          const run = await api.getRun(lastRun).catch(() => null);
          if (!cancelled && run && (run.status === "running" || run.status === "pending")) {
            setRunId(run.id);
            setRunStatus(run.status);
          }
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Failed to load project");
      }
    })();
    void refreshFiles();
    return () => {
      cancelled = true;
    };
  }, [projectId, refreshFiles]);

  // ── Run event handling ─────────────────────────────────────────────────────
  const statusTimer = useRef<string | null>(null);

  const handleEvent = useCallback((ev: AgentEvent) => {
    const d = ev.data ?? {};
    switch (ev.type) {
      case "agent.started":
        setRunStatus("running");
        setStatusLabel("Working…");
        setExecEntries([{
          id: `ev-${ev.sequence}`,
          kind: "status",
          title: "Agent run started",
        }]);
        break;

      case "agent.thinking": {
        const step = typeof d.step === "number" ? d.step : 1;
        setStatusLabel(`Thinking (step ${step})…`);
        break;
      }

      case "agent.message":
        setChatItems((prev) => [
          ...prev,
          { id: `msg-${ev.sequence}-${nextId()}`, role: "assistant", content: String(d.content ?? "") },
        ]);
        break;

      case "tool.started": {
        const tool = String(d.tool ?? "tool");
        const target = String((d.arguments as Record<string, unknown>)?.file_path ?? (d.arguments as Record<string, unknown>)?.command ?? "");
        setExecEntries((prev) => [
          ...prev,
          { id: `ev-${ev.sequence}`, kind: "tool", title: `→ ${tool}${target ? ` ${target}` : ""}`, pending: true },
        ]);
        break;
      }

      case "tool.completed": {
        const tool = String(d.tool ?? "");
        if (tool === "run_code" || tool === "run_command") {
          // Output handled by execution.output event
          break;
        }
        setExecEntries((prev) => {
          const idx = [...prev].reverse().findIndex((e) => e.pending);
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const copy = [...prev];
          const entry = copy[realIdx];
          copy[realIdx] = { ...entry, pending: false, detail: String(d.result ?? "").slice(0, 4000) };
          return copy;
        });
        break;
      }

      case "tool.failed": {
        setExecEntries((prev) => {
          const idx = [...prev].reverse().findIndex((e) => e.pending);
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const copy = [...prev];
          copy[realIdx] = { ...copy[realIdx], pending: false, kind: "error", title: `✗ ${copy[realIdx].title}`, detail: String(d.error ?? "").slice(0, 2000) };
          return copy;
        });
        break;
      }

      case "execution.output": {
        const tool = String(d.tool ?? "");
        const exitCode = typeof d.exit_code === "number" ? d.exit_code : 0;
        setExecEntries((prev) => [
          ...prev,
          {
            id: `ev-${ev.sequence}`,
            kind: exitCode === 0 ? "output" : "error",
            title: `$ ${tool}`,
            detail: String(d.output ?? "").slice(0, 4000),
          },
        ]);
        break;
      }

      case "file.created":
      case "file.modified":
      case "file.deleted": {
        const path = String(d.path ?? "");
        if (!path) break;
        const kind: FileChangeKind = ev.type === "file.created" ? "created" : ev.type === "file.modified" ? "modified" : "deleted";
        setChanges((prev) => new Map(prev).set(path, kind));
        setExecEntries((prev) => [...prev, { id: `ev-${ev.sequence}`, kind: "status", title: `${kind} ${path}` }]);
        // Refresh the on-disk view
        void refreshFiles();
        if (ev.type === "file.deleted") {
          // Remote a remotely-deleted file from open tabs immediately
          setTabs((prev) => prev.filter((t) => t.path !== path));
          setActivePath((cur) => (cur === path ? null : cur));
        } else {
          // Live-update open, clean (non-dirty) tabs with fresh content
          setTabs((prev) => {
            const target = prev.find((t) => t.path === path);
            if (!target || target.content !== target.savedContent) return prev;
            void api.readFile(projectId, path).then(({ content }) =>
              setTabs((cur) =>
                cur.map((t) =>
                  t.path === path && t.content === t.savedContent ? { ...t, content, savedContent: content } : t
                )
              )
            );
            return prev;
          });
        }
        break;
      }

      case "agent.completed":
        setRunStatus("completed");
        // A completed-with-warning run still gets a friendly label
        if (typeof d.warning === "string" && d.warning) {
          setStatusLabel("Completed (step limit reached)");
          setChatItems((prev) => [
            ...prev,
            { id: `warn-${ev.sequence}`, role: "assistant", content: `Run stopped: ${d.warning}` },
          ]);
        } else {
          setStatusLabel("Completed");
        }
        break;

      case "agent.failed":
        setRunStatus("failed");
        setStatusLabel("Failed");
        setChatItems((prev) => [
          ...prev,
          { id: `fail-${ev.sequence}`, role: "assistant", content: `Run failed: ${String(d.error ?? "unknown error")}`, error: true },
        ]);
        break;

      case "agent.cancelled":
        setRunStatus("cancelled");
        setStatusLabel("Cancelled");
        break;
    }
  }, [refreshFiles]);

  useRunEvents(runId, handleEvent);

  // ── Preview status polling ──────────────────────────────────────────────────
  const pollPreviewStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/projects/" + projectId + "/preview/status", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ project_id: projectId }),
      });

      if (!response.ok) return;

      const data = await response.json();
      const preview = data.preview;

      if (preview && preview.status) {
        setPreviewStatus(preview.status);
        setPreviewPort(preview.port ?? null);
        setPreviewFramework(preview.framework ?? null);
      }

      // Stop polling if preview is stopped or failed
      if (preview.status === "stopped" || preview.status === "failed") {
        // No need to stop polling explicitly - just don't update state
      }
    } catch (error) {
      console.error("Preview status poll error:", error);
    }
  }, [projectId]);

  useEffect(() => {
    // Start polling when a run is active
    let pollingId: NodeJS.Timeout | null = null;
    if (runStatus === "running" || runStatus === "pending") {
      pollingId = setInterval(pollPreviewStatus, 3000);
      pollPreviewStatus();
    }
    return () => {
      if (pollingId) clearInterval(pollPreviewStatus);
    };
  }, [runStatus, pollPreviewStatus, projectId]);

  // ── Chat actions ───────────────────────────────────────────────────────────
  const startRun = useCallback(
    async (prompt: string) => {
      if (!sessionId) return;
      setChatItems((prev) => [...prev, { id: nextId(), role: "user", content: prompt }]);
      setExecEntries([]);
      setRunStatus("pending");
      setStatusLabel("Starting…");
      try {
        const { run_id } = await api.startRun(projectId, sessionId, prompt);
        setRunId(run_id);
        window.sessionStorage.setItem(`cc_last_run_${projectId}`, run_id);
      } catch (err) {
        setRunStatus("failed");
        setStatusLabel("Failed");
        setChatItems((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: err instanceof ApiError ? err.message : "Could not start run",
            error: true,
          },
        ]);
      }
    },
    [projectId, sessionId]
  );

  const cancelRun = useCallback(async () => {
    if (!runIdRef.current) return;
    try {
      await api.cancelRun(runIdRef.current);
      setStatusLabel("Cancelling…");
    } catch {
      /* event stream will report the terminal state */
    }
  }, []);

  // ── Editor actions ─────────────────────────────────────────────────────────
  const openFile = useCallback(
    async (path: string) => {
      setActivePath(path);
      if (tabs.some((t) => t.path === path)) return;
      try {
        const { content } = await api.readFile(projectId, path);
        setTabs((prev) => [...prev, { path, content, savedContent: content, readOnly: false }]);
        setChanges((prev) => {
          const next = new Map(prev);
          next.delete(path);
          return next;
        });
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Failed to read file");
      }
    },
    [projectId, tabs]
  );

  const saveFile = useCallback(
    async (path: string) => {
      const tab = tabs.find((t) => t.path === path);
      if (!tab || tab.readOnly || tab.content === tab.savedContent) return;
      setSaving(true);
      try {
        await api.writeFile(projectId, path, tab.content);
        setTabs((prev) => prev.map((t) => (t.path === path ? { ...t, savedContent: t.content } : t)));
        setChanges((prev) => {
          const next = new Map(prev);
          if (next.get(path) === "created") next.delete(path);
          return next;
        });
        void refreshFiles();
      } catch (err) {
        setLoadError(err instanceof ApiError ? err.message : "Save failed");
      } finally {
        setSaving(false);
      }
    },
    [projectId, tabs, refreshFiles]
  );

  const statusBadge = useMemo(() => statusLabel, [statusLabel]);

  const terminalRun = runId !== null && (runStatus === "completed" || runStatus === "failed" || runStatus === "cancelled");

  return (
    <div className="flex h-screen flex-col bg-background">
      <header className="flex items-center gap-2 border-b px-3 py-1.5">
        <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs" asChild>
          <Link href="/workspace"><ArrowLeft className="h-3.5 w-3.5" /></Link>
        </Button>
        <span className="text-sm font-bold tracking-tight">CodeCrafter</span>
        <span className="text-xs text-muted-foreground">/</span>
        <span className="max-w-60 truncate text-xs font-medium">{project?.name ?? projectId}</span>
        <div className="ml-auto flex items-center gap-1">
          {filesLoading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          <Button variant="ghost" size="icon" className="h-7 w-7" title="Refresh workspace files" onClick={() => void refreshFiles()}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </header>

      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* File explorer */}
        <ResizablePanel defaultSize={18} minSize={12}>
          <div className="h-full border-r">
            <FileExplorer
              files={files}
              changes={changes}
              selectedPath={activePath}
              onSelect={(p) => void openFile(p)}
              onRefresh={() => void refreshFiles()}
              loading={filesLoading}
            />
          </div>
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-border" />

        {/* Editor + execution */}
        <ResizablePanel defaultSize={52}>
          <ResizablePanelGroup direction="vertical">
            <ResizablePanel defaultSize={70} minSize={25}>
              <div className="h-full">
                <CodeEditor
                  tabs={tabs}
                  activePath={activePath}
                  onSelectTab={setActivePath}
                  onCloseTab={(path) => {
                    setTabs((prev) => prev.filter((t) => t.path !== path));
                    setActivePath((cur) => (cur === path ? null : cur));
                  }}
                  onChangeContent={(path, content) =>
                    setTabs((prev) => prev.map((t) => (t.path === path ? { ...t, content } : t)))
                  }
                  onSave={saveFile}
                  onToggleReadOnly={(path) =>
                    setTabs((prev) => prev.map((t) => (t.path === path ? { ...t, readOnly: !t.readOnly } : t)))
                  }
                  saving={saving}
                />
              </div>
            </ResizablePanel>
            <ResizableHandle className="h-1 bg-border" />
            <ResizablePanel defaultSize={30} minSize={8}>
              <div className="h-full">
                <ExecutionPanel entries={execEntries} className="h-full" />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>

        <ResizableHandle className="w-1 bg-border" />

        {/* Agent chat */}
        <ResizablePanel defaultSize={30} minSize={18}>
          <div className="h-full border-l">
            <AgentChat
              items={chatItems}
              runStatus={runStatus}
              statusLabel={statusBadge}
              onCancel={cancelRun}
              onSubmit={(p) => void startRun(p)}
            />
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* Live preview panel */}
      <PreviewPanel
        projectId={projectId}
        runId={runId}
        runStatus={runStatus}
        previewStatus={previewStatus}
        previewPort={previewPort}
        previewFramework={previewFramework}
        onStop={() => {
          // Stop the preview via API
          fetch("/api/projects/" + projectId + "/preview/stop", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ project_id: projectId }),
          });
          setPreviewStatus("stopped");
        }}
        onRestart={() => {
          // Restart the preview via API
          fetch("/api/projects/" + projectId + "/preview/start", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ project_id: projectId }),
          });
        }}
      />
    </div>
  );
}