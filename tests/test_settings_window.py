from relay.settings import Settings
from relay.settings_window import ROWS, SettingsWindow


def test_a_slider_changes_the_setting():
    settings = Settings()
    window = SettingsWindow(settings)
    index = [row.key for row in ROWS].index("chinese_size")
    window.sliders[index].setDoubleValue_(40)
    window.actions.slider_(window.sliders[index])
    assert settings.chinese_size == 40
    assert window.values[index].stringValue() == "40 pt"
    assert window.dirty


def test_sentences_and_english_change_the_settings():
    settings = Settings()
    window = SettingsWindow(settings)
    window.count.setSelectedSegment_(2)
    window.actions.sentences_(window.count)
    window.english.performClick_(None)
    assert settings.sentences == 3
    assert settings.show_english is False


def test_reset_restores_the_controls():
    settings = Settings(chinese_size=40)
    window = SettingsWindow(settings)
    window.actions.reset_(None)
    assert settings == Settings()
    assert window.sliders[0].doubleValue() == Settings().chinese_size
