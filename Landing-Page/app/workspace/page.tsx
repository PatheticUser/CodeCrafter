"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FolderUp, GitBranch, Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { api, ApiError, type Project } from "@/lib/codecrafter";

export default function WorkspaceDashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);

  const loadProjects = useCallback(async () => {
    try {
      const list = await api.listProjects();
      setProjects(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reach backend. Is it running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setFormError(null);
    try {
      if (gitUrl.trim()) {
        await api.importGit(name.trim(), gitUrl.trim(), description.trim());
      } else {
        await api.createProject(name.trim(), description.trim());
      }
      setCreateOpen(false);
      setName("");
      setGitUrl("");
      setDescription("");
      await loadProjects();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteProject(deleteTarget.id);
      setDeleteTarget(null);
      await loadProjects();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 py-3">
          <Link href="/" className="text-sm font-bold tracking-tight">
            CodeCrafter
          </Link>
          <span className="text-xs text-muted-foreground">/ workspace</span>
          <Button size="sm" className="ml-auto gap-1.5" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> New project
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Create an empty project or import a public Git repository, then let the agent work inside it.
        </p>

        {error && (
          <div className="mt-4 rounded-md border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : projects.length === 0 ? (
          <div className="mt-10 flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center">
            <GitBranch className="h-8 w-8 text-muted-foreground" />
            <p className="font-medium">No projects yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Start by creating an empty project, or import a public repository and ask the agent to explore it.
            </p>
            <Button className="mt-2 gap-1.5" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> Create your first project
            </Button>
          </div>
        ) : (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/workspace/${project.id}`}
                className="group flex flex-col rounded-lg border p-4 transition-colors hover:border-foreground/30 hover:bg-accent/40"
              >
                <div className="flex items-start gap-2">
                  <GitBranch className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{project.name}</p>
                    <p className="line-clamp-2 min-h-8 text-xs text-muted-foreground">
                      {project.description || "No description"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span>{new Date(project.updated_at).toLocaleDateString()}</span>
                  {project.git_url && (
                    <span className="truncate rounded bg-muted px-1.5 py-0.5">git import</span>
                  )}
                  <div className="ml-auto flex items-center gap-1">
                    <span className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      Open <ArrowRight className="h-3 w-3" />
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-red-600"
                      title="Delete project"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setDeleteTarget(project);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* Create / import dialog */}
      <AlertDialog open={createOpen} onOpenChange={setCreateOpen}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>New project</AlertDialogTitle>
            <AlertDialogDescription>
              Create an empty project or clone a public Git repository into a sandboxed workspace.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Tabs defaultValue="empty">
            <TabsList className="w-full">
              <TabsTrigger value="empty" className="flex-1">
                Empty project
              </TabsTrigger>
              <TabsTrigger value="git" className="flex-1">
                Import from Git
              </TabsTrigger>
            </TabsList>
            <TabsContent value="git" className="mt-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <FolderUp className="h-3 w-3" /> Public HTTP/HTTPS repositories only.
              </div>
            </TabsContent>
          </Tabs>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="project-name">Name</Label>
              <Input
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-project"
                maxLength={100}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="project-git">Repository URL (optional)</Label>
              <Input
                id="project-git"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                placeholder="https://github.com/user/repo"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="project-desc">Description (optional)</Label>
              <Textarea
                id="project-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="min-h-16"
                placeholder="What is this project about?"
              />
            </div>
            {formError && (
              <p className="text-sm text-red-600 dark:text-red-400">{formError}</p>
            )}
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                void handleCreate();
              }}
              className="gap-1.5"
              disabled={busy || !name.trim()}
            >
              {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {gitUrl.trim() ? "Import" : "Create"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{deleteTarget?.name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the project&apos;s workspace directory, sessions, and run history.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep project</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 text-white hover:bg-red-700"
              onClick={(e) => {
                e.preventDefault();
                void handleDelete();
              }}
            >
              Delete permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
