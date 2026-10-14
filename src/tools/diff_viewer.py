"""Diff viewer tool for reviewing file changes with Monaco editor."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChangeRecord:
    """Records a single file change with before/after snapshots."""
    file_path: str
    operation: str  # "edit", "create", "delete"
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    # Bounded snapshots - keep only first/last N lines to avoid memory issues
    old_content_snapshot: str = field(default="")
    new_content_snapshot: str = field(default="")
    # Number of lines kept in each snapshot (limits memory usage)
    snapshot_lines: int = field(default=100)

    def get_old_preview(self) -> str:
        """Get a preview of the old content (first/last snapshot_lines)."""
        lines = self.old_content_snapshot.splitlines()
        if len(lines) <= self.snapshot_lines:
            return self.old_content_snapshot
        half = self.snapshot_lines // 2
        return "\n".join(lines[:half] + ["... truncated ..."] + lines[-half:])

    def get_new_preview(self) -> str:
        """Get a preview of the new content (first/last snapshot_lines)."""
        lines = self.new_content_snapshot.splitlines()
        if len(lines) <= self.snapshot_lines:
            return self.new_content_snapshot
        half = self.snapshot_lines // 2
        return "\n".join(lines[:half] + ["... truncated ..."] + lines[-half:])


@dataclass
class DiffResult:
    """Result of a diff operation between two file versions."""
    original: str
    modified: str
    file_path: str
    change_record: ChangeRecord | None = None

    # Compute the diff
    original_lines: list[str] = field(init=False)
    modified_lines: list[str] = field(init=False)
    diff_text: str = field(init=False)
    changes: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.original_lines = self.original.splitlines(keepends=True)
        self.modified_lines = self.modified.splitlines(keepends=True)
        self.diff_text = self._compute_unified_diff(self.original_lines, self.modified_lines)
        self.changes = self._analyze_changes(self.original_lines, self.modified_lines)
        self.summary = self._generate_summary()

    def _compute_unified_diff(
        self,
        original: list[str],
        modified: list[str],
    ) -> str:
        """Compute unified diff text."""
        diff = list(difflib.unified_diff(
            original,
            modified,
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
            lineterm="",
        ))
        return "\n".join(diff)

    def _analyze_changes(
        self,
        original: list[str],
        modified: list[str],
    ) -> dict[str, Any]:
        """Analyze changes between original and modified versions."""
        changes = {
            "added": [],
            "deleted": [],
            "modified": [],
            "unchanged": [],
        }

        # Use SequenceMatcher for detailed analysis
        matcher = difflib.SequenceMatcher(None, "".join(original), "".join(modified))

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                chunk = "".join(original[i1:i2])
                content = chunk[:200] if len(chunk) > 200 else chunk
                changes["deleted"].append({
                    "content": content,
                    "start_line": sum(1 for line in original[:i1] if line.endswith("\n")) + 1,
                    "end_line": sum(1 for line in original[:i2] if line.endswith("\n")) + 1,
                })
            elif tag == "insert":
                chunk = "".join(modified[j1:j2])
                content = chunk[:200] if len(chunk) > 200 else chunk
                changes["added"].append({
                    "content": content,
                    "start_line": sum(1 for line in modified[:j1] if line.endswith("\n")) + 1,
                    "end_line": sum(1 for line in modified[:j2] if line.endswith("\n")) + 1,
                })
            elif tag == "replace":
                old_chunk = "".join(original[i1:i2])
                new_chunk = "".join(modified[j1:j2])
                old_content = old_chunk[:200] if len(old_chunk) > 200 else old_chunk
                new_content = new_chunk[:200] if len(new_chunk) > 200 else new_chunk
                changes["modified"].append({
                    "old": old_content,
                    "new": new_content,
                    "old_start": sum(1 for line in original[:i1] if line.endswith("\n")) + 1,
                    "old_end": sum(1 for line in original[:i2] if line.endswith("\n")) + 1,
                    "new_start": sum(1 for line in modified[:j1] if line.endswith("\n")) + 1,
                    "new_end": sum(1 for line in modified[:j2] if line.endswith("\n")) + 1,
                })
            elif tag == "equal":
                joined = "".join(original[i1:i2])
                content = joined[:200] if len(joined) > 200 else joined
                changes["unchanged"].append({
                    "content": content,
                })

        return changes

    def _generate_summary(self) -> dict[str, Any]:
        """Generate a summary of changes."""
        total_added = len(self.changes["added"])
        total_deleted = len(self.changes["deleted"])
        total_modified = len(self.changes["modified"])
        return {
            "total_lines_original": len(self.original.splitlines()),
            "total_lines_modified": len(self.modified.splitlines()),
            "lines_added": total_added,
            "lines_deleted": total_deleted,
            "lines_modified": total_modified,
            "has_significant_changes": total_added + total_deleted + total_modified > 5,
        }


def generate_diff(
    original_content: str,
    modified_content: str,
    file_path: str,
    change_record: ChangeRecord | None = None,    ) -> dict[str, Any]:
    """Generate a diff result between two file contents.

    Args:
        original_content: The original file content
        modified_content: The modified file content
        file_path: Path to the file being diffed
        change_record: Optional ChangeRecord tracking this modification

    Returns:
        Dictionary with diff analysis results
    """
    result = DiffResult(original_content, modified_content, file_path, change_record)

    return {
        "file_path": result.file_path,
        "diff_text": result.diff_text,
        "changes": {
            "added": [c["content"] for c in result.changes["added"]],
            "deleted": [c["content"] for c in result.changes["deleted"]],
            "modified": [{"old": c["old"], "new": c["new"]} for c in result.changes["modified"]],
        },
        "summary": result.summary,
    }


def format_monaco_diff(
    diff_result: dict[str, Any],
    show_summary: bool = True,
) -> str:
    """Format diff result for Monaco editor display.

    Creates a structured HTML/JSON representation suitable for
    embedding in a Monaco diff editor widget.

    Args:
        diff_result: Result from generate_diff()
        show_summary: Whether to include change summary

    Returns:
        JSON string formatted for Monaco diff editor
    """
    # Parse the diff into structured data for Monaco
    original = diff_result.get("original", "")
    modified = diff_result.get("modified", "")
    changes = diff_result.get("changes", {})
    summary = diff_result.get("summary", {})

    monaco_data = {
        "original": original,
        "modified": modified,
        "changes": changes,
        "summary": summary if show_summary else None,
    }

    return json.dumps(monaco_data, ensure_ascii=False, indent=2)


def get_change_highlights(
    diff_result: dict[str, Any],
) -> dict[str, list[dict[str, int]]]:
    """Get line number highlights for added/deleted/modified lines.

    Returns data suitable for Monaco editor gutter annotations.

    Args:
        diff_result: Result from generate_diff()

    Returns:
        Dictionary with line highlights for original and modified sides
    """
    highlights = {
        "original": [],  # Line numbers in original to highlight
        "modified": [],  # Line numbers in modified to highlight
    }

    changes = diff_result.get("changes", {})

    # Add highlights for deleted lines (appear in original)
    for change in changes.get("deleted", []):
        content = change.get("content", "")
        # Approximate line numbers based on content
        lines = content.splitlines()
        for i, line in enumerate(lines):
            highlights["original"].append({"line": i + 1, "className": "deleted"})

    # Add highlights for added lines (appear in modified)
    for change in changes.get("added", []):
        content = change.get("content", "")
        lines = content.splitlines()
        for i, line in enumerate(lines):
            highlights["modified"].append({"line": i + 1, "className": "added"})

    # Add highlights for modified lines
    for change in changes.get("modified", []):
        old_lines = change.get("old", "").splitlines()
        new_lines = change.get("new", "").splitlines()
        for i in range(min(len(old_lines), len(new_lines))):
            highlights["original"].append({"line": i + 1, "className": "modified"})
            highlights["modified"].append({"line": i + 1, "className": "modified"})

    return highlights
