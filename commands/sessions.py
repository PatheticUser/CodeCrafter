"""Built-in commands: session management."""

from commands.base import BaseCommand
from ui.display import c, dim, Colors, Icons, show_error
from services.logger import logger


class SessionsListCommand(BaseCommand):
    name = "sessions"
    description = "List all saved sessions"

    def execute(self, args, context):
        from chat_session import list_sessions

        sessions = list_sessions()
        if not sessions:
            print(f"  {dim(Icons.INFO)}  No saved sessions found.")
            return True

        print()
        print(f"  {c(Icons.BRAIN, Colors.CYAN)}  {c('Saved Sessions', Colors.BOLD)}")
        print(f"  {dim('─' * 52)}")
        for i, s in enumerate(sessions):
            marker = c(Icons.ARROW, Colors.CYAN) if i == 0 else " "
            info_line = f"{s['modified']}  |  {s['messages']} msgs"
            print(f"  {marker}  {c(s['name'], Colors.CYAN)}  {dim(info_line)}")
        print()
        return True


class SessionNewCommand(BaseCommand):
    name = "session new"
    description = "Start a new session"

    def execute(self, args, context):
        from core.workspace import scan_workspace_tree
        from config import WORKING_DIR

        session_mgr = context["session_mgr"]
        new_name = session_mgr.new_session()
        print(f"  {c(Icons.SUCCESS, Colors.GREEN)}  New session: {c(new_name, Colors.CYAN)}")
        return True


class SessionLoadCommand(BaseCommand):
    name = "session load"
    description = "Load a specific session"

    def execute(self, args, context):
        if not args:
            show_error("Usage: session load <name>")
            return True

        session_mgr = context["session_mgr"]
        try:
            name, msg_count = session_mgr.load(args)
            print(
                f"  {c(Icons.SUCCESS, Colors.GREEN)}  "
                f"Loaded session: {c(name, Colors.CYAN)} ({msg_count} messages)"
            )
        except Exception as e:
            logger.error("Failed to load session: %s", e, exc_info=True)
            show_error(f"Failed to load session: {e}")
        return True


class SessionDeleteCommand(BaseCommand):
    name = "session delete"
    description = "Delete a session"

    def execute(self, args, context):
        from chat_session import delete_session_file

        if not args:
            show_error("Usage: session delete <name>")
            return True

        session_mgr = context["session_mgr"]
        if args == session_mgr.current_session_name:
            show_error("Cannot delete the active session. Switch first.")
            return True

        if delete_session_file(args):
            print(f"  {c(Icons.SUCCESS, Colors.GREEN)}  Deleted session: {c(args, Colors.CYAN)}")
        else:
            show_error(f"Session '{args}' not found.")
        return True


class ClearCommand(BaseCommand):
    name = "clear"
    description = "Clear current session history"

    def execute(self, args, context):
        session_mgr = context["session_mgr"]
        session_mgr.clear()
        print(f"  {dim(Icons.INFO)}  Session cleared")
        return True


class ExitCommand(BaseCommand):
    name = "exit"
    aliases = ["quit", "q", "e"]
    description = "Save session and exit"

    def execute(self, args, context):
        from ui.display import show_exit_banner

        session_mgr = context["session_mgr"]
        user_name = context["user_name"]
        session_mgr.save()
        show_exit_banner(user_name)
        context["should_exit"] = True
        return True
