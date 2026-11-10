from earfish.settings import Settings, load, save


def test_settings_survive_a_restart(tmp_path):
    path = tmp_path / "folder" / "settings.json"
    save(Settings(chinese_size=40, show_english=False), path)
    loaded = load(path)
    assert loaded.chinese_size == 40
    assert loaded.show_english is False


def test_a_missing_file_gives_the_defaults(tmp_path):
    assert load(tmp_path / "none.json") == Settings()


def test_a_damaged_file_gives_the_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json")
    assert load(path) == Settings()
    path.write_text("[1, 2]")
    assert load(path) == Settings()


def test_odd_values_are_kept_in_range(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"chinese_size": 999, "sentences": 0, "width": "wide", "show_english": "yes"}')
    settings = load(path)
    assert settings.chinese_size == 60
    assert settings.sentences == 1
    assert settings.width == Settings().width
    assert settings.show_english is True


def test_reset_restores_the_defaults():
    settings = Settings(chinese_size=40, show_english=False)
    settings.reset()
    assert settings == Settings()
