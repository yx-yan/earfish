"""The meeting transcript: one Markdown file for each session."""

from datetime import datetime
from pathlib import Path

FOLDER = Path.home() / "Documents" / "Relay"


class Transcript:
    """Created on the first sentence, so a session with no speech leaves no file."""

    def __init__(self, started: datetime, folder: Path = FOLDER):
        self.started = started
        self.path = folder / f"{started:%Y-%m-%d %H-%M}.md"

    def add(self, at: datetime, english: str, chinese: str) -> None:
        """Append and close at once, so a crash loses nothing already translated."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        heading = "" if self.path.exists() else f"# Meeting {self.started:%Y-%m-%d %H:%M}\n\n"
        entry = f"**{at:%H:%M:%S}** {english}\n\n"
        if chinese != english:
            entry += f"{chinese}\n\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(heading + entry)
