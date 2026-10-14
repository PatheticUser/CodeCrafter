"use client";

import { useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  RefreshCw,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { FileMeta } from "@/lib/codecrafter";

interface TreeNode {
  name: string;
  path: string;
  children: TreeNode[];
  file?: FileMeta;
}

export type FileChangeKind = "created" | "modified" | "deleted";

interface FileExplorerProps {
  files: FileMeta[];
  /** Changed file paths keyed by change kind, used for indicator dots. */
  changes: Map<string, FileChangeKind>;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onRefresh: () => void;
  loading?: boolean;
}

function buildTree(files: FileMeta[]): TreeNode {
  const root: TreeNode = { name: "", path: "", children: [] };
  for (const file of files) {
    const parts = file.path.split("/").filter(Boolean);
    let node = root;
    parts.forEach((part, i) => {
      const isLeaf = i === parts.length - 1;
      const path = parts.slice(0, i + 1).join("/");
      let child = node.children.find((c) => c.name === part && c.path === path);
      if (!child) {
        child = { name: part, path, children: [] };
        node.children.push(child);
      }
      if (isLeaf) child.file = file;
      node = child;
    });
  }
  const sortNode = (n: TreeNode) => {
    n.children.sort((a, b) => {
      const aDir = !a.file, bDir = !b.file;
      if (aDir !== bDir) return aDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    n.children.forEach(sortNode);
  };
  sortNode(root);
  return root;
}

function TreeRow({
  node,
  depth,
  selectedPath,
  changes,
  expanded,
  toggleDir,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  changes: Map<string, FileChangeKind>;
  expanded: Set<string>;
  toggleDir: (path: string) => void;
  onSelect: (path: string) => void;
}) {
  const isFile = !!node.file;
  const isOpen = expanded.has(node.path) || depth === 0;
  const change = changes.get(node.path);

  if (isFile) {
    return (
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className={cn(
          "flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs hover:bg-accent",
          selectedPath === node.path && "bg-accent"
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <File className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="truncate">{node.name}</span>
        {change && (
          <span
            aria-label={`file ${change}`}
            className={cn(
              "ml-auto h-1.5 w-1.5 shrink-0 rounded-full",
              change === "created" && "bg-emerald-500",
              change === "modified" && "bg-amber-500",
              change === "deleted" && "bg-red-500"
            )}
          />
        )}
      </button>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => toggleDir(node.path)}
        className="flex w-full items-center gap-1 rounded px-2 py-1 text-left text-xs font-medium hover:bg-accent"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isOpen ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        <Folder className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="truncate">{node.name || "root"}</span>
      </button>
      {isOpen &&
        node.children.map((child) => (
          <TreeRow
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            changes={changes}
            expanded={expanded}
            toggleDir={toggleDir}
            onSelect={onSelect}
          />
        ))}
    </div>
  );
}

export function FileExplorer({
  files,
  changes,
  selectedPath,
  onSelect,
  onRefresh,
  loading,
}: FileExplorerProps) {
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const visibleFiles = useMemo(
    () => (filter ? files.filter((f) => f.path.toLowerCase().includes(filter.toLowerCase())) : files),
    [files, filter]
  );
  const tree = useMemo(() => buildTree(visibleFiles), [visibleFiles]);

  const toggleDir = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1 border-b px-2 py-1.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Files</span>
        <div className="ml-auto flex items-center gap-1">
          {loading && <span className="text-[10px] text-muted-foreground">loading…</span>}
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onRefresh} title="Refresh files">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="border-b p-1.5">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter files…"
            className="h-7 pl-7 text-xs"
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="py-1">
          {files.length === 0 ? (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">
              No files yet. Ask the agent to create something.
            </p>
          ) : (
            tree.children.map((child) => (
              <TreeRow
                key={child.path}
                node={child}
                depth={0}
                selectedPath={selectedPath}
                changes={changes}
                expanded={expanded}
                toggleDir={toggleDir}
                onSelect={onSelect}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
