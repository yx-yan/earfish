"""Play a 16 kHz mono WAV through the whole pipeline, in real time, for testing."""

import argparse
import threading
import time
import wave
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from earfish.asr import load_recognizer
from earfish.audio import BLOCK, SAMPLE_RATE
from earfish.interpreter import Interpreter, State
from earfish.translate import Translator


class WavFile:
    always_on = False

    def __init__(self, path: Path):
        with wave.open(str(path)) as f:
            self.samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)

    def start(self, on_audio) -> None:
        for start in range(0, len(self.samples), BLOCK):
            on_audio(self.samples[start : start + BLOCK])
            time.sleep(BLOCK / SAMPLE_RATE)

    def stop(self) -> None:
        pass


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--transcripts", type=Path, default=Path("transcripts"))
    args = parser.parse_args()

    interpreter = Interpreter(load_recognizer, Translator(), args.transcripts)
    threading.Thread(target=interpreter.recognize, daemon=True).start()
    threading.Thread(target=interpreter.translate, daemon=True).start()
    while interpreter.state is State.LOADING:
        time.sleep(0.1)
    interpreter.start(WavFile(args.wav))
    interpreter.stop()
    while not (interpreter.audio.empty() and interpreter.sentences.empty()):
        time.sleep(0.1)
    time.sleep(3)  # Let the last translation finish.
    print("\n".join(line.chinese for line in interpreter.caption.lines))


if __name__ == "__main__":
    main()
