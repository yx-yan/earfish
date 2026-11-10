from datetime import datetime

from earfish.transcript import Transcript

STARTED = datetime(2026, 11, 7, 14, 30)


def test_writes_each_sentence_as_it_arrives(tmp_path):
    transcript = Transcript(STARTED, tmp_path)
    transcript.add(datetime(2026, 11, 7, 14, 30, 5), "Hello.", "你好。")
    assert transcript.path.name == "2026-11-07 14-30.md"
    assert transcript.path.read_text() == "# Meeting 2026-11-07 14:30\n\n**14:30:05** Hello.\n\n你好。\n\n"

    transcript.add(datetime(2026, 11, 7, 14, 30, 9), "Bye.", "再见。")
    assert transcript.path.read_text().count("# Meeting") == 1
    assert transcript.path.read_text().endswith("**14:30:09** Bye.\n\n再见。\n\n")


def test_an_untranslated_sentence_appears_once(tmp_path):
    transcript = Transcript(STARTED, tmp_path)
    transcript.add(STARTED, "Hello.", "Hello.")
    assert transcript.path.read_text().count("Hello.") == 1


def test_no_speech_leaves_no_file(tmp_path):
    Transcript(STARTED, tmp_path)
    assert list(tmp_path.iterdir()) == []
