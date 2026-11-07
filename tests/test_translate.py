from types import SimpleNamespace

from openai import OpenAIError

from relay.translate import Translator


def chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


class FakeClient:
    def __init__(self, result):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.result = result

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def broken_stream():
    yield chunk("你")
    raise OpenAIError("slow")


def test_streams_the_translation():
    seen = []
    result = Translator(FakeClient([chunk("你"), chunk("好")])).translate("Hello", seen.append)
    assert result.text == "你好"
    assert not result.fell_back
    assert seen == ["你", "你好"]


def test_api_failure_keeps_the_english():
    result = Translator(FakeClient(OpenAIError("down"))).translate("Hello")
    assert result.text == "Hello"
    assert result.fell_back


def test_failure_during_the_stream_keeps_the_english():
    result = Translator(FakeClient(broken_stream())).translate("Hello")
    assert result.text == "Hello"
    assert result.fell_back


def test_empty_answer_keeps_the_english():
    assert Translator(FakeClient([])).translate("Hello").fell_back


def test_sends_only_the_latest_sentences_as_context():
    client = FakeClient([chunk("好")])
    translator = Translator(client)
    for sentence in ["One.", "Two.", "Three."]:
        client.result = [chunk("好")]
        translator.translate(sentence)
    translator.client.result = [chunk("好")]
    translator.translate("Four.")
    request = client.calls[-1]["messages"][1]["content"]
    assert "One." not in request
    assert request == "Earlier:\nTwo.\nThree.\n\nTranslate:\nFour."
