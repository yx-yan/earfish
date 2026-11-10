"""How the subtitle looks, remembered between launches."""

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

PATH = Path.home() / "Library" / "Application Support" / "Earfish" / "settings.json"

LIMITS = {
    "chinese_size": (16, 60),
    "english_size": (12, 48),
    "width": (400, 1600),
    "opacity": (0, 100),
    "position": (0, 100),
    "sentences": (1, 3),
}


@dataclass
class Settings:
    chinese_size: int = 26
    english_size: int = 18
    width: int = 960
    opacity: int = 78  # Percent.
    position: int = 0  # Percent of the way up the screen.
    sentences: int = 2
    show_english: bool = True

    def reset(self) -> None:
        for field in fields(self):
            setattr(self, field.name, field.default)


def load(path: Path = PATH) -> Settings:
    """Read the settings. A damaged file gives the defaults, and odd values are clamped."""
    settings = Settings()
    try:
        saved = json.loads(path.read_text())
    except (OSError, ValueError):
        return settings
    if not isinstance(saved, dict):
        return settings
    for field in fields(settings):
        value = saved.get(field.name)
        if field.name == "show_english" and isinstance(value, bool):
            settings.show_english = value
        elif field.name in LIMITS and type(value) in (int, float):
            low, high = LIMITS[field.name]
            setattr(settings, field.name, int(min(high, max(low, value))))
    return settings


def save(settings: Settings, path: Path = PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2))
