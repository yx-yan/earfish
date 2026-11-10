"""Connects audio, recognition, translation, subtitles and the transcript."""

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Empty, Queue

from earfish.audio import Source
from earfish.transcript import FOLDER, Transcript

MAX_CAPTION_LINES = 3
CAPTION_SECONDS = 8
NO_AUDIO_SECONDS = 3


class State(Enum):
    LOADING = "Loading speech model..."
    READY = "Ready"
    LISTENING = "Listening"


@dataclass
class Sentence:
    english: str
    at: datetime
    transcript: Transcript


@dataclass(frozen=True)
class Line:
    english: str
    chinese: str = ""


class Caption:
    """What the subtitle shows. Kept free of AppKit so it can be tested."""

    def __init__(self):
        self.lines = deque(maxlen=MAX_CAPTION_LINES)
        self.current = None
        self.updated = 0.0

    def begin(self, english: str, now: float) -> None:
        """Show the English straight away, while the translation is on its way."""
        self.current = Line(english)
        self.updated = now

    def update(self, chinese: str, now: float) -> None:
        self.current = Line(self.current.english, chinese)
        self.updated = now

    def commit(self, chinese: str, now: float) -> None:
        self.lines.append(Line(self.current.english, chinese))
        self.current = None
        self.updated = now

    def visible(self, count: int, now: float) -> list[Line]:
        if now - self.updated > CAPTION_SECONDS:
            return []
        lines = list(self.lines)
        if self.current:
            lines.append(self.current)
        return lines[-count:]


def merge(sentences: list[Sentence]) -> Sentence:
    """Join a backlog into one request, so subtitles catch up instead of falling behind."""
    first = sentences[0]
    return Sentence(" ".join(s.english for s in sentences), first.at, first.transcript)


class Interpreter:
    def __init__(self, load_recognizer, translator, folder: Path = FOLDER):
        self.load_recognizer = load_recognizer
        self.translator = translator
        self.folder = folder
        self.audio = Queue()  # Audio blocks, a Transcript to start, or None to finish.
        self.sentences = Queue()
        self.caption = Caption()
        self.state = State.READY
        self.message = ""
        self.source = None
        self.started = 0.0
        self.heard = False

    @property
    def running(self) -> bool:
        return self.state is not State.READY

    def start(self, source: Source) -> None:
        """Audio is queued while the model loads, so the first words are not lost."""
        self.audio.put(Transcript(datetime.now(), self.folder))
        self.state = State.LOADING
        self.listen(source)

    def listen(self, source: Source) -> None:
        """Change the source. A running session keeps its transcript."""
        if self.source:
            self.source.stop()
        self.source = source
        self.started = time.monotonic()
        self.heard = False
        self.message = ""
        source.start(self.hear)

    def stop(self) -> None:
        self.source.stop()
        self.source = None
        self.audio.put(None)
        self.state = State.READY
        self.message = ""

    def hear(self, block) -> None:
        self.heard = True
        self.audio.put(block)

    def check_audio(self) -> None:
        """A microphone without permission delivers nothing and raises no error."""
        if not self.running or self.heard or not self.source.always_on:
            return
        if time.monotonic() - self.started > NO_AUDIO_SECONDS:
            self.message = "No audio. Allow the microphone in System Settings."

    def recognize(self) -> None:
        """Worker thread. It owns the model, because MLX stays on the thread that loaded it.

        The model is loaded when a session starts and freed when it ends, so Earfish holds
        little memory while it is not listening.
        """
        recognizer = None
        transcript = None
        while True:
            item = self.audio.get()
            if isinstance(item, Transcript):
                transcript = item
                if recognizer is None:
                    recognizer = self.load_recognizer()
                if self.state is State.LOADING:
                    self.state = State.LISTENING
            elif item is None:
                self.send(recognizer.flush(), transcript)
                recognizer.close()
                recognizer = None
            else:
                self.send(recognizer.feed(item), transcript)

    def send(self, sentences: list[str], transcript: Transcript) -> None:
        for english in sentences:
            self.sentences.put(Sentence(english, datetime.now(), transcript))

    def translate(self) -> None:
        """Worker thread for the network calls."""
        while True:
            self.translate_next()

    def translate_next(self) -> None:
        backlog = [self.sentences.get()]
        try:
            while True:
                backlog.append(self.sentences.get_nowait())
        except Empty:
            pass

        sentence = merge(backlog)
        self.caption.begin(sentence.english, time.monotonic())
        result = self.translator.translate(
            sentence.english,
            lambda text: self.caption.update(text, time.monotonic()),
        )
        self.caption.commit(result.text, time.monotonic())
        sentence.transcript.add(sentence.at, sentence.english, result.text)
        self.message = "Translation failed, showing English" if result.fell_back else ""
