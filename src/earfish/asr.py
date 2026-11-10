"""Streaming English speech recognition, cut into sentences for translation."""

import re

import numpy as np

from earfish.audio import SAMPLE_RATE, loudness

MODEL = "moona3k/mlx-qwen3-asr-0.6b-8bit"
CHUNK_SECONDS = 0.5
CONTEXT_SECONDS = 30  # A 15 s window split words at its edges.
ROLLBACK_WORDS = 3  # Trailing words the model may still change. Each one adds waiting time.
SPEECH_LEVEL = 0.15
PAUSE_SECONDS = 0.8  # At 0.5 s, normal pauses inside a sentence cut it into fragments.
MAX_WORDS = 25

SENTENCE_END = re.compile(r"""[.?!]["')]*$""")


class Segmenter:
    """Finds finished sentences in text that keeps growing.

    It counts words instead of characters because the recognizer can still
    respell earlier stable text, which shifts character positions.
    """

    def __init__(self):
        self.done = 0

    def take(self, text: str, final: bool = False) -> list[str]:
        words = text.split()
        sentences = []
        start = self.done
        for index in range(start, len(words)):
            if SENTENCE_END.search(words[index]):
                sentences.append(" ".join(words[start : index + 1]))
                start = index + 1

        rest = words[start:]
        if final and rest:
            sentences.append(" ".join(rest))
            start = len(words)
        elif len(rest) >= MAX_WORDS:
            end = long_sentence_cut(rest)
            sentences.append(" ".join(rest[:end]))
            start += end
        self.done = start
        return [sentence for sentence in sentences if any(c.isalnum() for c in sentence)]


def long_sentence_cut(words: list[str]) -> int:
    """Cut after the last comma, or at the end when there is none."""
    for index in range(len(words) - 1, 0, -1):
        if words[index].endswith((",", ";", ":")):
            return index + 1
    return len(words)


class Recognizer:
    def __init__(self, session):
        self.session = session
        self.stream = None
        self.segmenter = Segmenter()
        self.quiet = 0.0

    def feed(self, block: np.ndarray) -> list[str]:
        """Take a block of audio and return any sentences it finished."""
        if loudness(block) < SPEECH_LEVEL:
            self.quiet += len(block) / SAMPLE_RATE
            if self.stream is None:
                return []  # Silence makes speech models invent text.
            if self.quiet >= PAUSE_SECONDS:
                return self.flush()
        else:
            self.quiet = 0.0

        if self.stream is None:
            self.stream = self.session.init_streaming(
                language="English",
                chunk_size_sec=CHUNK_SECONDS,
                max_context_sec=CONTEXT_SECONDS,
                unfixed_token_num=ROLLBACK_WORDS,
            )
        self.stream = self.session.feed_audio(block.astype(np.float32) / 32768, self.stream)
        return self.segmenter.take(self.stream.stable_text)

    def flush(self) -> list[str]:
        """End the stream, which also keeps its text from growing without limit."""
        if self.stream is None:
            return []
        stream = self.session.finish_streaming(self.stream)
        sentences = self.segmenter.take(stream.text, final=True)
        self.stream = None
        self.segmenter = Segmenter()
        return sentences


def load_recognizer() -> Recognizer:
    from mlx_qwen3_asr import Session

    return Recognizer(Session(model=MODEL))
