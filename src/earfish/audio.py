"""Audio sources. Each one delivers 16 kHz mono 16-bit blocks to a callback."""

import subprocess
import threading
from collections.abc import Callable
from typing import Protocol

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000
BLOCK = SAMPLE_RATE // 10
QUIET_DB, LOUD_DB = -55, -25  # Room noise to loud speech.
HELPER = "/Applications/Earfish.app/Contents/MacOS/audiotap"


class Source(Protocol):
    always_on: bool  # Whether it delivers blocks even when nothing is making sound.

    def start(self, on_audio: Callable[[np.ndarray], None]) -> None: ...
    def stop(self) -> None: ...


class Microphone:
    """Keeps one input stream open, because stopping a stream can deadlock CoreAudio."""

    always_on = True

    def __init__(self):
        self.on_audio = None
        self.stream = None

    def _on_block(self, data, *_):
        # macOS sends all zeros without microphone access, which must not count as audio.
        if self.on_audio and not is_silent(data):
            self.on_audio(data[:, 0].copy())

    def start(self, on_audio) -> None:
        self.on_audio = on_audio
        if self.stream is None:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=BLOCK,
                callback=self._on_block,
            )
            self.stream.start()

    def stop(self) -> None:
        self.on_audio = None


class ComputerAudio:
    """Reads what the Mac is playing from the audiotap helper."""

    always_on = False  # The helper gets no audio while the Mac is silent.

    def __init__(self, helper: str = HELPER):
        self.helper = helper
        self.process = None

    def start(self, on_audio) -> None:
        self.process = subprocess.Popen([self.helper], stdout=subprocess.PIPE)
        threading.Thread(target=self._read, args=(self.process, on_audio), daemon=True).start()

    def _read(self, process, on_audio) -> None:
        while data := process.stdout.read(BLOCK * 2):
            on_audio(np.frombuffer(data, dtype=np.int16))

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            self.process = None


def loudness(samples: np.ndarray) -> float:
    """Map a block of audio to 0-1, on a decibel scale because that is how loudness feels."""
    rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2)) / 32768
    if rms == 0:
        return 0.0
    return float(np.clip((20 * np.log10(rms) - QUIET_DB) / (LOUD_DB - QUIET_DB), 0, 1))


def is_silent(samples: np.ndarray) -> bool:
    """True for digital silence. A working microphone always picks up some noise."""
    return not np.any(samples)
