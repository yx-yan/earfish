from types import SimpleNamespace

import numpy as np

from earfish.asr import MAX_WORDS, Recognizer, Segmenter

LOUD = np.full(1600, 8000, dtype=np.int16)
QUIET = np.zeros(1600, dtype=np.int16)


class FakeSession:
    def __init__(self, stable="", text=""):
        self.stable, self.text = stable, text
        self.fed = 0
        self.finished = 0

    def init_streaming(self, **_):
        return SimpleNamespace(stable_text="", text="")

    def feed_audio(self, _, stream):
        self.fed += 1
        return SimpleNamespace(stable_text=self.stable, text=self.text)

    def finish_streaming(self, stream):
        self.finished += 1
        return SimpleNamespace(stable_text=self.text, text=self.text)


def test_segmenter_returns_each_sentence_once():
    segmenter = Segmenter()
    assert segmenter.take("Hello there. How are") == ["Hello there."]
    assert segmenter.take("Hello there. How are you? Fine") == ["How are you?"]
    assert segmenter.take("Hello there. How are you? Fine") == []


def test_segmenter_survives_earlier_words_being_respelled():
    segmenter = Segmenter()
    segmenter.take("Their fine. Next")
    assert segmenter.take("They're fine. Next one.") == ["Next one."]


def test_segmenter_keeps_an_unfinished_sentence_until_final():
    segmenter = Segmenter()
    assert segmenter.take("no punctuation yet") == []
    assert segmenter.take("no punctuation yet", final=True) == ["no punctuation yet"]


def test_segmenter_cuts_a_long_sentence_at_the_last_comma():
    words = ["word"] * (MAX_WORDS - 5) + ["comma,"] + ["word"] * 4
    assert Segmenter().take(" ".join(words)) == [" ".join(words[: MAX_WORDS - 4])]


def test_segmenter_cuts_a_long_sentence_without_commas():
    words = ["word"] * MAX_WORDS
    assert Segmenter().take(" ".join(words)) == [" ".join(words)]


def test_segmenter_drops_a_lone_full_stop():
    assert Segmenter().take(". Hello there.") == ["Hello there."]


def test_silence_before_speech_never_reaches_the_model():
    session = FakeSession()
    recognizer = Recognizer(session)
    assert recognizer.feed(QUIET) == []
    assert session.fed == 0


def test_a_pause_finishes_the_sentence_and_starts_over():
    session = FakeSession(stable="Good", text="Good morning everyone")
    recognizer = Recognizer(session)
    recognizer.feed(LOUD)
    sentences = []
    for _ in range(11):
        sentences += recognizer.feed(QUIET)
    assert sentences == ["Good morning everyone"]
    assert session.finished == 1
    assert recognizer.stream is None


def test_flush_without_speech_does_nothing():
    assert Recognizer(FakeSession()).flush() == []
