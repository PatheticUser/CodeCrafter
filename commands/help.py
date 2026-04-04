"""Built-in command: help — display available commands."""

from commands.base import BaseCommand
from ui.display import c, dim, Colors, Icons, BANNER_WIDTH


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"

    def execute(self, args, context):
        print()
        print(f"  {c(Icons.INFO, Colors.CYAN)}  {c('Commands', Colors.BOLD)}")
        print(f"  {dim('─' * BANNER_WIDTH)}")
        cmds = [
            ("help", "Show this help message"),
            ("sessions", "List all saved sessions"),
            ("session new", "Start a new session"),
            ("session load <name>", "Load a specific session"),
            ("session delete <name>", "Delete a session"),
            ("clear", "Clear current session history"),
            ("exit / quit", "Save session and exit"),
        ]
        for cmd, desc in cmds:
            print(f"  {c(cmd, Colors.YELLOW):<30s}  {dim(desc)}")
        print()
        return True
