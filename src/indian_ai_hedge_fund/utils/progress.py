from rich.console import Console
from rich.style import Style
from rich.text import Text
from typing import Dict, Optional
import threading
import traceback

console = Console()


class AgentProgress:
    """Manages progress tracking for multiple agents using simple print statements."""

    def __init__(self):
        self.agent_status: Dict[str, Dict[str, str]] = {}
        self.lock = threading.Lock()
        self.started = False
        # Keep track of the last printed lines per agent to potentially overwrite
        self._last_lines: Dict[str, int] = {}

    def start(self):
        """Indicate that progress tracking has started."""
        with self.lock:
            if not self.started:
                # console.print("[dim]Progress tracking started.[/dim]")
                self.started = True

    def stop(self):
        """Indicate that progress tracking has stopped."""
        with self.lock:
            if self.started:
                # Optional: Print a final summary or clear status
                # console.print("[dim]Progress tracking stopped.[/dim]")
                self.started = False
                # Clear agent statuses for next run if needed
                self.agent_status.clear()
                self._last_lines.clear()

    def update_status(self, agent_name: str, ticker: Optional[str] = None, status: str = ""):
        """Update and print the status of an agent."""
        with self.lock:
            if not self.started:
                # Don't print if not started, prevents premature messages
                return

            try:
                # Ensure agent entry exists
                if agent_name not in self.agent_status:
                    self.agent_status[agent_name] = {"status": "", "ticker": None}

                # Update specific fields
                current_ticker = self.agent_status[agent_name].get("ticker")
                current_status = self.agent_status[agent_name].get("status", "")

                new_ticker = ticker if ticker is not None else current_ticker
                new_status = status if status else current_status

                # Only print if something actually changed
                if new_ticker != current_ticker or new_status != current_status:
                    self.agent_status[agent_name]["ticker"] = new_ticker
                    self.agent_status[agent_name]["status"] = new_status

                    # Format and print the update
                    self._print_status(agent_name)

            except Exception as e:
                console.print(f"[red]Error updating/printing status for {agent_name}: {str(e)}[/red]")
                # traceback.print_exc() # Optional: more detailed error logging

    def _print_status(self, agent_name: str):
        """Formats and prints the status for a specific agent."""
        info = self.agent_status.get(agent_name)
        if not info:
            return

        status = info.get("status", "")
        ticker = info.get("ticker", None)

        # --- Status Styling ---
        if not status: # Don't print empty status
             return

        symbol = "⋯"
        style = Style(color="yellow")
        if status.lower() == "done" or "complete" in status.lower():
            style = Style(color="green", bold=True)
            symbol = "✓"
        elif "error" in status.lower():
            style = Style(color="red", bold=True)
            symbol = "✗"
        # Add more specific styling if needed (e.g., for 'fetching', 'analyzing')

        # --- Formatting ---
        agent_display = agent_name.replace("_agent", "").replace("_", " ").title()
        status_text = Text()
        status_text.append(f"{symbol} ", style=style)
        status_text.append(f"{agent_display:<25}", style=Style(bold=True)) # Fixed width for alignment
        if ticker:
            status_text.append(f"[{ticker}] ", style=Style(color="cyan"))
        status_text.append(status, style=style)

        # --- Printing ---
        # Simple print for robustness in threads
        console.print(status_text)

        # --- (Optional) Overwriting logic (might be unstable with threads/agent output) ---
        # line_count = status_text.count('\n') + 1
        # if agent_name in self._last_lines:
        #     # Move cursor up and clear lines (ANSI escape codes)
        #     console.print(f"\x1b[{self._last_lines[agent_name]}A\x1b[J", end="")
        # console.print(status_text)
        # self._last_lines[agent_name] = line_count


# Create a global instance
progress = AgentProgress()
