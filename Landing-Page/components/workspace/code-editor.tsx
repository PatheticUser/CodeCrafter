"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Editor from "@monaco-editor/react";
import { File, Loader2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EditorTab {
  path: string;
  content: string;
  savedContent: string;
  readOnly: boolean;
}

/** Map file extensions to Monaco language ids. */
function languageFor(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    py: "python",
    js: "javascript",
    jsx: "javascript",
    mjs: "javascript",
    ts: "typescript",
    tsx: "typescript",
    json: "json",
    html: "html",
    css: "css",
    scss: "scss",
    md: "markdown",
    yml: "yaml",
    yaml: "yaml",
    toml: "ini",
    sh: "shell",
    bash: "shell",
    sql: "sql",
    rs: "rust",
    go: "go",
    java: "java",
    c: "c",
    h: "c",
    cpp: "cpp",
    hpp: "cpp",
    cs: "csharp",
    rb: "ruby",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    xml: "xml",
    svg: "xml",
  };
  return map[ext] ?? "plaintext";
}

interface CodeEditorProps {
  tabs: EditorTab[];
  activePath: string | null;
  onSelectTab: (path: string) => void;
  onCloseTab: (path: string) => void;
  onChangeContent: (path: string, content: string) => void;
  onSave: (path: string) => Promise<void>;
  onToggleReadOnly: (path: string) => void;
  saving: boolean;
}

export function CodeEditor({
  tabs,
  activePath,
  onSelectTab,
  onCloseTab,
  onChangeContent,
  onSave,
  onToggleReadOnly,
  saving,
}: CodeEditorProps) {
  const activeTab = tabs.find((t) => t.path === activePath) ?? null;
  const saveRef = useRef(onSave);
  saveRef.current = onSave;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (activePath) void saveRef.current(activePath);
      }
    },
    [activePath]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!activeTab) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
        <File className="h-8 w-8" />
        <p className="text-sm">Select a file from the explorer to view or edit it.</p>
      </div>
    );
  }

  const isDirty = activeTab.content !== activeTab.savedContent;

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="flex h-9 items-center gap-0.5 border-b bg-muted/40 px-1">
        {tabs.map((tab) => {
          const dirty = tab.content !== tab.savedContent;
          return (
            <button
              key={tab.path}
              type="button"
              onClick={() => onSelectTab(tab.path)}
              className={cn(
                "group flex h-8 items-center gap-1.5 rounded-t border-x border-t px-2.5 text-xs",
                tab.path === activePath
                  ? "border-border bg-background text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <span className="max-w-40 truncate">{tab.path.split("/").pop()}</span>
              {dirty && <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-label="unsaved changes" />}
              <X
                className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-60"
                onClick={(e) => {
                  e.stopPropagation();
                  onCloseTab(tab.path);
                }}
              />
            </button>
          );
        })}
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b px-2 py-1">
        <span className="truncate text-[11px] text-muted-foreground">{activeTab.path}</span>
        <div className="ml-auto flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[11px]"
            onClick={() => onToggleReadOnly(activeTab.path)}
          >
            {activeTab.readOnly ? "Locked (read-only)" : "Editable"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 px-2 text-[11px]"
            disabled={!isDirty || activeTab.readOnly || saving}
            onClick={() => void onSave(activeTab.path)}
          >
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
            Save
            <kbd className="ml-1 rounded bg-muted px-1 text-[9px]">⌘S</kbd>
          </Button>
        </div>
      </div>

      {/* Monaco */}
      <div className="flex-1 overflow-hidden">
        <Editor
          key={activeTab.path}
          height="100%"
          language={languageFor(activeTab.path)}
          theme="vs-dark"
          value={activeTab.content}
          onChange={(value) => onChangeContent(activeTab.path, value ?? "")}
          options={{
            readOnly: activeTab.readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            automaticLayout: true,
            scrollBeyondLastLine: false,
            tabSize: 2,
            renderWhitespace: "selection",
          }}
          loading={
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          }
        />
      </div>
    </div>
  );
}
