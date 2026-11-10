from earfish.onboarding import Check, has_key, incomplete


def test_incomplete_until_every_check_is_done():
    done = Check("Done", "", lambda: True)
    missing = Check("Missing", "", lambda: False)
    assert incomplete((done, missing))
    assert not incomplete((done,))


def test_key_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert not has_key()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    assert has_key()
