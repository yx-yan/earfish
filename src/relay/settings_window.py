"""A window for changing how the subtitle looks. Changes show at once."""

from dataclasses import dataclass

from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFont,
    NSMakeRect,
    NSObject,
    NSSegmentedControl,
    NSSegmentSwitchTrackingSelectOne,
    NSSlider,
    NSTextAlignmentRight,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)

from relay.settings import LIMITS, Settings

WIDTH = 420
ROW_HEIGHT = 36
MARGIN = 20
LABEL_WIDTH = 120
VALUE_WIDTH = 56
FOOTER_HEIGHT = 56


@dataclass(frozen=True)
class Row:
    title: str
    key: str
    unit: str


ROWS = (
    Row("Chinese Size", "chinese_size", " pt"),
    Row("English Size", "english_size", " pt"),
    Row("Subtitle Width", "width", " pt"),
    Row("Background", "opacity", "%"),
    Row("Height on Screen", "position", "%"),
)


class SettingsActions(NSObject):
    def slider_(self, sender):
        self.owner.slide(sender.tag(), round(sender.doubleValue()))

    def sentences_(self, sender):
        self.owner.choose_sentences(sender.selectedSegment() + 1)

    def english_(self, sender):
        self.owner.toggle_english(bool(sender.state()))

    def reset_(self, _):
        self.owner.reset()

    def close_(self, sender):
        sender.window().close()


class SettingsWindow:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.dirty = False
        self.actions = SettingsActions.alloc().init()
        self.actions.owner = self
        self.sliders = []
        self.values = []

        height = ROW_HEIGHT * (len(ROWS) + 2) + MARGIN + FOOTER_HEIGHT
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIDTH, height),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Subtitle Settings")
        self.window.setReleasedWhenClosed_(False)
        content = self.window.contentView()

        def row_y(index: int) -> int:
            return height - MARGIN - ROW_HEIGHT * (index + 1) + 8

        for index, row in enumerate(ROWS):
            y = row_y(index)
            content.addSubview_(self.title(row.title, y))
            low, high = LIMITS[row.key]
            slider = NSSlider.sliderWithValue_minValue_maxValue_target_action_(
                getattr(settings, row.key), low, high, self.actions, "slider:"
            )
            slider.setContinuous_(True)
            slider.setTag_(index)
            slider.setFrame_(NSMakeRect(
                MARGIN + LABEL_WIDTH, y, WIDTH - MARGIN * 2 - LABEL_WIDTH - VALUE_WIDTH, 22
            ))
            content.addSubview_(slider)
            value = NSTextField.labelWithString_("")
            value.setFont_(NSFont.monospacedDigitSystemFontOfSize_weight_(12, 0))
            value.setTextColor_(NSColor.secondaryLabelColor())
            value.setAlignment_(NSTextAlignmentRight)
            value.setFrame_(NSMakeRect(WIDTH - MARGIN - VALUE_WIDTH, y + 2, VALUE_WIDTH, 18))
            content.addSubview_(value)
            self.sliders.append(slider)
            self.values.append(value)

        y = row_y(len(ROWS))
        content.addSubview_(self.title("Sentences Shown", y))
        self.count = NSSegmentedControl.segmentedControlWithLabels_trackingMode_target_action_(
            ["1", "2", "3"], NSSegmentSwitchTrackingSelectOne, self.actions, "sentences:"
        )
        self.count.setFrame_(NSMakeRect(MARGIN + LABEL_WIDTH, y - 2, 120, 26))
        content.addSubview_(self.count)

        y = row_y(len(ROWS) + 1)
        self.english = NSButton.checkboxWithTitle_target_action_(
            "Show English above the Chinese", self.actions, "english:"
        )
        self.english.setFrame_(NSMakeRect(MARGIN + LABEL_WIDTH, y, 260, 22))
        content.addSubview_(self.english)

        reset = NSButton.buttonWithTitle_target_action_("Reset", self.actions, "reset:")
        reset.setFrame_(NSMakeRect(MARGIN, 16, 84, 28))
        content.addSubview_(reset)
        done = NSButton.buttonWithTitle_target_action_("Done", self.actions, "close:")
        done.setFrame_(NSMakeRect(WIDTH - MARGIN - 84, 16, 84, 28))
        done.setKeyEquivalent_("\r")
        content.addSubview_(done)
        self.refresh()

    def title(self, text: str, y: int) -> NSTextField:
        label = NSTextField.labelWithString_(text)
        label.setFont_(NSFont.systemFontOfSize_(13))
        label.setFrame_(NSMakeRect(MARGIN, y + 1, LABEL_WIDTH, 18))
        return label

    def refresh(self) -> None:
        for row, slider, value in zip(ROWS, self.sliders, self.values):
            number = getattr(self.settings, row.key)
            slider.setDoubleValue_(number)
            value.setStringValue_(f"{number}{row.unit}")
        self.count.setSelectedSegment_(self.settings.sentences - 1)
        self.english.setState_(int(self.settings.show_english))

    def slide(self, index: int, number: int) -> None:
        row = ROWS[index]
        setattr(self.settings, row.key, number)
        self.values[index].setStringValue_(f"{number}{row.unit}")
        self.dirty = True

    def choose_sentences(self, count: int) -> None:
        self.settings.sentences = count
        self.dirty = True

    def toggle_english(self, show: bool) -> None:
        self.settings.show_english = show
        self.dirty = True

    def reset(self) -> None:
        self.settings.reset()
        self.refresh()
        self.dirty = True

    def show(self) -> None:
        self.window.center()
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)

    @property
    def visible(self) -> bool:
        return bool(self.window.isVisible())
