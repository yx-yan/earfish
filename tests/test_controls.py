from earfish.controls import Controls

NAMES = ["Computer Audio", "Microphone"]


def make_controls():
    calls = []
    controls = Controls(
        NAMES,
        NAMES[0],
        on_toggle=lambda: calls.append("toggle"),
        on_source=calls.append,
        on_subtitle=lambda: calls.append("subtitle"),
        on_transcripts=lambda: calls.append("transcripts"),
        on_quit=lambda: calls.append("quit"),
    )
    return controls, calls


def test_buttons_call_their_handlers():
    controls, calls = make_controls()
    for button in controls.panel.contentView().subviews():
        if hasattr(button, "performClick_") and button.className() == "NSButton":
            button.performClick_(None)
    assert calls == ["toggle", "subtitle", "transcripts", "quit"]


def test_choosing_a_source_reports_its_name():
    controls, calls = make_controls()
    controls.sources.setSelectedSegment_(1)
    controls.target.source_(controls.sources)
    assert calls == ["Microphone"]


def test_update_shows_the_state():
    controls, _ = make_controls()
    controls.update("Listening", "Stop")
    assert controls.status.stringValue() == "Listening"
    assert controls.toggle.title() == "Stop"
