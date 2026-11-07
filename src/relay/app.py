"""Menu bar app: subtitles for what the Mac is playing or the microphone hears."""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from dotenv import load_dotenv

from relay.asr import load_recognizer
from relay.audio import ComputerAudio, Microphone
from relay.controls import Controls
from relay.interpreter import Interpreter, Line, State
from relay.onboarding import SetupWindow, incomplete
from relay.overlay import Overlay
from relay.settings import load, save
from relay.settings_window import SettingsWindow
from relay.transcript import FOLDER
from relay.translate import Translator

ICON_DIR = Path(__file__).parent / "icons"
ICONS = {state: str(ICON_DIR / f"{state.name.lower()}.png") for state in State}
WARNING_ICON = str(ICON_DIR / "warning.png")
SAMPLE = Line("This is how your subtitles will look.", "字幕会显示成这样。")


class MenuBar(rumps.App):
    def __init__(self, interpreter: Interpreter, start_now: bool):
        super().__init__("Relay", icon=ICONS[State.LOADING], template=True, quit_button=None)
        self.interpreter = interpreter
        self.start_now = start_now
        self.overlay = Overlay()
        self.setup = SetupWindow()
        self.settings = load()
        self.settings_window = SettingsWindow(self.settings)
        self.greeted = False
        self.sources = {"Computer Audio": ComputerAudio(), "Microphone": Microphone()}
        self.chosen = "Computer Audio"
        self.status = rumps.MenuItem(State.LOADING.value)
        self.toggle = rumps.MenuItem("Start", callback=self.on_toggle)
        self.source_items = {
            name: rumps.MenuItem(name, callback=self.on_source) for name in self.sources
        }
        self.source_items[self.chosen].state = 1
        self.menu = [
            self.status,
            rumps.separator,
            self.toggle,
            rumps.separator,
            *self.source_items.values(),
            rumps.separator,
            rumps.MenuItem("Subtitle Settings...", callback=lambda _: self.settings_window.show()),
            rumps.MenuItem("Open Transcripts", callback=lambda _: open_transcripts()),
            rumps.MenuItem("Setup...", callback=lambda _: self.setup.show()),
            rumps.MenuItem("Quit Relay", callback=lambda _: self.quit()),
        ]
        self.controls = Controls(
            list(self.sources),
            self.chosen,
            on_toggle=lambda: self.on_toggle(None),
            on_source=self.choose,
            on_subtitle=self.settings_window.show,
            on_transcripts=open_transcripts,
            on_quit=self.quit,
        )
        self.controls.show()

    @rumps.timer(0.1)
    def refresh(self, _):
        """Update the UI here because AppKit must only be touched on the main thread."""
        interpreter = self.interpreter
        if self.start_now and interpreter.state is State.READY:
            self.start_now = False
            self.on_toggle(None)
        interpreter.check_audio()
        status = interpreter.message or interpreter.state.value
        toggle = "Stop" if interpreter.state is State.LISTENING else "Start"
        self.status.title = status
        self.toggle.title = toggle
        self.controls.update(status, toggle, enabled=interpreter.state is not State.LOADING)
        icon = WARNING_ICON if interpreter.message else ICONS[interpreter.state]
        if icon != self.icon:
            self.icon = icon
        if not self.greeted:
            self.greeted = True
            if incomplete():
                self.setup.show()
        self.show_subtitle()

    def show_subtitle(self) -> None:
        settings = self.settings
        lines = self.interpreter.caption.visible(settings.sentences, time.monotonic())
        if not lines and self.settings_window.visible:
            lines = [SAMPLE] * settings.sentences  # A preview, so changes show at once.
        self.overlay.show(lines, settings)
        if self.settings_window.dirty:
            self.settings_window.dirty = False
            save(settings)

    def on_toggle(self, _):
        interpreter = self.interpreter
        if interpreter.state is State.READY:
            interpreter.start(self.sources[self.chosen])
        elif interpreter.state is State.LISTENING:
            interpreter.stop()

    def on_source(self, item):
        self.choose(item.title)
        self.controls.sources.setSelectedSegment_(list(self.sources).index(item.title))

    def choose(self, name: str) -> None:
        self.source_items[self.chosen].state = 0
        self.chosen = name
        self.source_items[name].state = 1
        if self.interpreter.state is State.LISTENING:
            self.interpreter.listen(self.sources[self.chosen])

    def quit(self) -> None:
        self.sources["Computer Audio"].stop()
        quit_now()


def open_transcripts() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    subprocess.run(["open", str(FOLDER)])


def quit_now(*_) -> None:
    os._exit(0)  # Skip closing the stream, which is where CoreAudio can deadlock.


def main() -> None:
    load_dotenv()
    interpreter = Interpreter(load_recognizer, Translator())

    signal.signal(signal.SIGINT, quit_now)
    threading.Thread(target=interpreter.recognize, daemon=True).start()
    threading.Thread(target=interpreter.translate, daemon=True).start()
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    MenuBar(interpreter, start_now="RELAY_START" in os.environ).run()


if __name__ == "__main__":
    main()
