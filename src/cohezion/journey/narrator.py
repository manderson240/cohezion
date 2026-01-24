import asyncio
import sys
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.style import Style

class NarrativeEngine:
    """
    Orchestrates immersive narration with typewriter effects and interactive pauses.
    """
    def __init__(self, console=None):
        self.console = console or Console()

    async def typewrite(self, text, style="italic #a1c4fd", speed=0.03):
        """Prints text with a typewriter effect, handling Rich markup."""

        # Parse markup into a Rich Text object
        parsed_markup = Text.from_markup(text, style=style)
        length = len(parsed_markup)

        with Live(Text(), console=self.console, transient=True, refresh_per_second=20) as live:
            for i in range(length + 1):
                # Reveal up to character i
                live.update(parsed_markup[:i])
                await asyncio.sleep(speed)

        # Finally print it permanently
        self.console.print(parsed_markup)

    async def narrate_panel(self, title, content, border_style="#4facfe", delay=1.0):
        """Displays a narrated panel with a delay."""
        panel = Panel(
            Text.from_markup(content),
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            padding=(1, 2)
        )
        self.console.print(panel)
        await asyncio.sleep(delay)

    async def prompt_continue(self, prompt="[dim]Press ENTER to continue your journey...[/dim]"):
        """Pauses for user input to continue."""
        self.console.print(prompt)
        # Use asyncio to wait for input without blocking the loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)

class JourneyRegistry:
    """
    Manages the registration and discovery of interactive 'Voyages'.
    """
    def __init__(self):
        self.voyages = {}

    def register_voyage(self, name, description, entry_point):
        self.voyages[name] = {
            "description": description,
            "entry_point": entry_point
        }

    def get_voyage(self, name):
        return self.voyages.get(name)

    def list_voyages(self):
        return self.voyages
