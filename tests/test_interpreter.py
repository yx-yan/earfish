import threading
import time
from datetime import datetime

import numpy as np

from earfish.interpreter import CAPTION_SECONDS, Caption, Interpreter, Line, Sentence, State, merge
from earfish.transcript import Transcript
from earfish.translate import Translation

NOW = datetime(2026, 11, 7, 14, 30)


class FakeTranslator:
    def __init__(self, fell_back=False):
        self.requests = []
        self.fell_back = fell_back

    def translate(self, english, on_text):
        self.requests.append(english)
        on_text("译")
        return Translation(english if self.fell_back else "译文", self.fell_back)


class FakeSource:
    def __init__(self, always_on=True):
        self.always_on = always_on
        self.running = False

    def start(self, on_audio):
        self.running = True
        self.on_audio = on_audio

    def stop(self):
        self.running = False


def test_caption_shows_english_before_the_translation_arrives():
    caption = Caption()
    caption.begin("Hello.", 0)
    assert caption.visible(2, 0) == [Line("Hello.")]
    caption.update("你", 0)
    assert caption.visible(2, 0) == [Line("Hello.", "你")]


def test_caption_keeps_the_latest_lines():
    caption = Caption()
    for line in ["一", "二", "三"]:
        caption.begin(line, 0)
        caption.commit(line, 0)
    assert [line.chinese for line in caption.visible(2, 0)] == ["二", "三"]
    assert [line.chinese for line in caption.visible(1, 0)] == ["三"]


def test_caption_counts_the_sentence_being_translated():
    caption = Caption()
    for line in ["一", "二"]:
        caption.begin(line, 0)
        caption.commit(line, 0)
    caption.begin("Three.", 0)
    assert [line.english for line in caption.visible(2, 0)] == ["二", "Three."]


def test_caption_clears_after_a_while():
    caption = Caption()
    caption.begin("One.", 0)
    caption.commit("一", 0)
    assert caption.visible(2, CAPTION_SECONDS + 1) == []


def test_merge_joins_a_backlog(tmp_path):
    transcript = Transcript(NOW, tmp_path)
    merged = merge([Sentence("One.", NOW, transcript), Sentence("Two.", NOW, transcript)])
    assert merged.english == "One. Two."


def test_translation_catches_up_in_one_request(tmp_path):
    translator = FakeTranslator()
    interpreter = Interpreter(None, translator, tmp_path)
    transcript = Transcript(NOW, tmp_path)
    interpreter.send(["One.", "Two.", "Three."], transcript)
    interpreter.translate_next()
    assert translator.requests == ["One. Two. Three."]
    assert list(interpreter.caption.lines) == [Line("One. Two. Three.", "译文")]
    assert "译文" in transcript.path.read_text()


def test_failed_translation_is_shown_and_saved_in_english(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(fell_back=True), tmp_path)
    transcript = Transcript(NOW, tmp_path)
    interpreter.send(["Hello."], transcript)
    interpreter.translate_next()
    assert list(interpreter.caption.lines) == [Line("Hello.", "Hello.")]
    assert "Hello." in transcript.path.read_text()
    assert interpreter.message


def test_warns_when_a_source_delivers_nothing(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(), tmp_path)
    interpreter.start(FakeSource())
    interpreter.started -= 10
    interpreter.check_audio()
    assert interpreter.message


def test_a_silent_computer_is_not_a_problem(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(), tmp_path)
    interpreter.start(FakeSource(always_on=False))
    interpreter.started -= 10
    interpreter.check_audio()
    assert interpreter.message == ""


def test_no_warning_once_audio_arrives(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(), tmp_path)
    interpreter.start(FakeSource())
    interpreter.hear(np.zeros(1600, dtype=np.int16))
    interpreter.started -= 10
    interpreter.check_audio()
    assert interpreter.message == ""


def test_changing_source_stops_the_old_one(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(), tmp_path)
    first, second = FakeSource(), FakeSource()
    interpreter.start(first)
    interpreter.listen(second)
    assert not first.running and second.running
    assert interpreter.running


def test_stop_asks_the_recognizer_to_finish(tmp_path):
    interpreter = Interpreter(None, FakeTranslator(), tmp_path)
    source = FakeSource()
    interpreter.start(source)
    interpreter.stop()
    assert not source.running
    assert interpreter.state is State.READY
    assert isinstance(interpreter.audio.get(), Transcript)
    assert interpreter.audio.get() is None


class FakeRecognizer:
    def __init__(self):
        self.closed = False

    def feed(self, block):
        return []

    def flush(self):
        return []

    def close(self):
        self.closed = True


def wait_for(condition):
    deadline = time.monotonic() + 2
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.01)


def test_the_model_loads_on_start_and_is_freed_on_stop(tmp_path):
    loaded = []
    interpreter = Interpreter(lambda: loaded.append(FakeRecognizer()) or loaded[-1], FakeTranslator(), tmp_path)
    threading.Thread(target=interpreter.recognize, daemon=True).start()
    assert interpreter.state is State.READY and not loaded

    interpreter.start(FakeSource())
    assert interpreter.state is State.LOADING
    wait_for(lambda: interpreter.state is State.LISTENING)

    interpreter.stop()
    wait_for(lambda: loaded[0].closed)
    interpreter.start(FakeSource())
    wait_for(lambda: len(loaded) == 2)
