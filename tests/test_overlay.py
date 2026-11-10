from earfish.interpreter import Line
from earfish.overlay import Overlay, subtitle_rows
from earfish.settings import Settings


def test_english_goes_above_the_chinese():
    assert subtitle_rows([Line("Hello.", "你好。")], True) == [("Hello.", True), ("你好。", False)]


def test_english_can_be_hidden():
    assert subtitle_rows([Line("Hello.", "你好。")], False) == [("你好。", False)]


def test_english_shows_alone_while_the_translation_is_coming():
    assert subtitle_rows([Line("Hello.")], True) == [("Hello.", True)]
    assert subtitle_rows([Line("Hello.")], False) == []


def test_a_failed_translation_appears_once():
    assert subtitle_rows([Line("Hello.", "Hello.")], True) == [("Hello.", False)]


def test_a_bigger_font_makes_a_taller_subtitle():
    overlay = Overlay()
    lines = [Line("Hello.", "你好。")]
    overlay.show(lines, Settings(chinese_size=20))
    small = overlay.panel.frame().size.height
    overlay.show(lines, Settings(chinese_size=50))
    assert overlay.panel.frame().size.height > small
    overlay.show([], Settings())


def test_position_moves_the_subtitle_up():
    overlay = Overlay()
    lines = [Line("Hello.", "你好。")]
    overlay.show(lines, Settings(position=0))
    low = overlay.panel.frame().origin.y
    overlay.show(lines, Settings(position=100))
    assert overlay.panel.frame().origin.y > low
    overlay.show([], Settings())


def test_width_limits_long_text():
    overlay = Overlay()
    lines = [Line("word " * 80, "字" * 120)]
    overlay.show(lines, Settings(width=500))
    assert overlay.panel.frame().size.width <= 500
    overlay.show([], Settings())
