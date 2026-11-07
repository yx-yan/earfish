import relay.app as app
from relay.interpreter import Interpreter
from relay.settings import Settings


def make_menu_bar(monkeypatch, tmp_path):
    saved = []
    monkeypatch.setattr(app, "load", Settings)
    monkeypatch.setattr(app, "save", saved.append)
    interpreter = Interpreter(None, None, tmp_path)
    return app.MenuBar(interpreter, start_now=False), saved


def test_settings_window_previews_a_sample(monkeypatch, tmp_path):
    menu_bar, _ = make_menu_bar(monkeypatch, tmp_path)
    menu_bar.settings_window.window.orderFront_(None)
    menu_bar.show_subtitle()
    assert menu_bar.overlay.panel.isVisible()
    menu_bar.settings_window.window.orderOut_(None)
    menu_bar.show_subtitle()
    assert not menu_bar.overlay.panel.isVisible()


def test_a_change_is_saved_once(monkeypatch, tmp_path):
    menu_bar, saved = make_menu_bar(monkeypatch, tmp_path)
    menu_bar.settings_window.slide(0, 40)
    menu_bar.show_subtitle()
    menu_bar.show_subtitle()
    assert len(saved) == 1
    assert saved[0].chinese_size == 40
