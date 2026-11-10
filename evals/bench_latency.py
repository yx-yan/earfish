"""Measure the delay from the end of each sentence to its subtitle.

Speech comes from macOS `say`, so the moment each sentence ends is known exactly. It
is played through the real recognizer and DeepSeek at real-time speed. Calls the API.
"""

import argparse
import difflib
import re
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

import earfish.asr as asr
from earfish.audio import BLOCK, SAMPLE_RATE
from earfish.interpreter import Interpreter, State
from earfish.translate import Translator

SENTENCES = """
Thanks everyone for joining the call this morning.
I want to start with a quick update on the new release.
The team finished the migration earlier than we expected last week.
However we found a serious problem with the payment service on Friday.
Some customers were charged twice when they refreshed the checkout page.
We rolled back the change and contacted everyone who was affected.
Right now the main risk is the database upgrade planned for next month.
If that slips we will have to move the launch date as well.
Can someone from the platform team walk us through the current plan?
I think we should test the upgrade on a copy of the production data first.
That sounds reasonable but it will take at least another two weeks.
We also need more people on support during the first few days.
Marketing would like a clear answer before they book the campaign.
Let me summarize what we have agreed so far in this meeting.
We will keep the original date unless the test shows any new problems.
Sarah will write the plan and share it with the whole group tomorrow.
David will talk to finance about the extra cost for the support team.
Please send me any questions you have before the end of the day.
Does anybody have anything else they would like to raise right now?
Great, thank you all for your time and have a good afternoon.
""".strip().splitlines()

SILENCE = 200  # Peak level below which the synthesized audio counts as silent.


def speak(text: str, rate: int, folder: Path) -> np.ndarray:
    path = folder / "sentence.wav"
    subprocess.run(
        ["say", "-v", "Samantha", "-r", str(rate), "-o", str(path),
         "--file-format=WAVE", "--data-format=LEI16@16000", text],
        check=True,
    )
    with wave.open(str(path)) as f:
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    loud = np.flatnonzero(np.abs(samples.astype(np.int32)) > SILENCE)
    return samples[loud[0] : loud[-1] + 1]


def build(rate: int, gap: float, folder: Path) -> tuple[np.ndarray, list[float]]:
    """Return the audio and the time each sentence ends."""
    parts, ends, position = [], [], 0
    silence = np.zeros(int(gap * SAMPLE_RATE), dtype=np.int16)
    for sentence in SENTENCES:
        speech = speak(sentence, rate, folder)
        position += len(speech)
        ends.append(position / SAMPLE_RATE)
        parts += [speech, silence]
        position += len(silence)
    parts.append(np.zeros(2 * SAMPLE_RATE, dtype=np.int16))
    return np.concatenate(parts), ends


class Replay:
    always_on = False

    def __init__(self, samples: np.ndarray):
        self.samples = samples
        self.began = 0.0

    def start(self, on_audio) -> None:
        self.began = time.monotonic()
        for index, start in enumerate(range(0, len(self.samples), BLOCK)):
            time.sleep(max(0, self.began + (index + 1) * BLOCK / SAMPLE_RATE - time.monotonic()))
            on_audio(self.samples[start : start + BLOCK])

    def stop(self) -> None:
        pass


class TimedTranslator:
    def __init__(self):
        self.inner = Translator()
        self.calls = []

    def translate(self, english, on_text):
        call = {"english": english, "start": time.monotonic(), "first": None}

        def seen(text):
            call["first"] = call["first"] or time.monotonic()
            on_text(text)

        result = self.inner.translate(english, seen)
        call["done"] = time.monotonic()
        call["failed"] = result.fell_back
        self.calls.append(call)
        return result


class TimedInterpreter(Interpreter):
    def __init__(self, *args):
        super().__init__(*args)
        self.emitted = []

    def send(self, sentences, transcript):
        now = time.monotonic()
        self.emitted += [(now, sentence) for sentence in sentences]
        super().send(sentences, transcript)


def words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def measure(interpreter, translator, began, ends) -> list[dict]:
    """Find which emitted sentence finished each spoken sentence, and its times."""
    spoken = [(word, index) for index, s in enumerate(SENTENCES) for word in words(s)]
    heard = [(word, index) for index, (_, s) in enumerate(interpreter.emitted) for word in words(s)]
    matcher = difflib.SequenceMatcher(None, [w for w, _ in spoken], [w for w, _ in heard], autojunk=False)
    last = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            last[spoken[block.a + offset][1]] = heard[block.b + offset][1]

    interpreter.accuracy = sum(b.size for b in matcher.get_matching_blocks()) / len(spoken)
    rows = []
    for index, end in enumerate(ends):
        if index not in last:
            continue
        emitted_at, text = interpreter.emitted[last[index]]
        call = next((c for c in translator.calls if text in c["english"] and c["done"] >= emitted_at), None)
        if call is None or call["first"] is None:
            continue
        rows.append({
            "recognized": emitted_at - began - end,
            "queued": call["start"] - emitted_at,
            "first": call["first"] - began - end,
            "done": call["done"] - began - end,
        })
    return rows


def run(rate: int, gap: float, folder: Path) -> None:
    audio, ends = build(rate, gap, folder)
    speech_seconds = ends[-1] - gap * (len(SENTENCES) - 1)
    pace = len(words(" ".join(SENTENCES))) / speech_seconds * 60

    translator = TimedTranslator()
    interpreter = TimedInterpreter(asr.load_recognizer, translator, folder / "transcripts")
    threading.Thread(target=interpreter.recognize, daemon=True).start()
    threading.Thread(target=interpreter.translate, daemon=True).start()
    while interpreter.state is State.LOADING:
        time.sleep(0.1)

    replay = Replay(audio)
    interpreter.start(replay)
    interpreter.stop()
    while not (interpreter.audio.empty() and interpreter.sentences.empty()):
        time.sleep(0.1)
    time.sleep(3)

    rows = measure(interpreter, translator, replay.began, ends)
    failed = sum(call["failed"] for call in translator.calls)

    def stat(key):
        values = np.array([row[key] for row in rows])
        return f"{np.median(values):5.2f} / {np.percentile(values, 90):5.2f} / {values.max():5.2f}"

    print(
        f"{pace:3.0f} wpm, gap {gap:.1f}s | matched {len(rows)}/{len(ends)}, failed {failed}, "
        f"words right {interpreter.accuracy:.1%}, pieces {len(interpreter.emitted)} | "
        f"recognized {stat('recognized')} | first Chinese {stat('first')} | "
        f"full Chinese {stat('done')}  (median / p90 / max, seconds)",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default="175:0.3,230:0.3,280:0.3,175:2", help="rate:gap,...")
    parser.add_argument("--pause", type=float, default=asr.PAUSE_SECONDS)
    parser.add_argument("--chunk", type=float, default=asr.CHUNK_SECONDS)
    parser.add_argument("--rollback", type=int, default=asr.ROLLBACK_WORDS)
    args = parser.parse_args()
    load_dotenv()
    asr.PAUSE_SECONDS, asr.CHUNK_SECONDS, asr.ROLLBACK_WORDS = args.pause, args.chunk, args.rollback
    print(f"pause {args.pause}s, chunk {args.chunk}s, rollback {args.rollback} words", flush=True)
    with tempfile.TemporaryDirectory() as folder:
        for case in args.cases.split(","):
            rate, gap = case.split(":")
            run(int(rate), float(gap), Path(folder))
