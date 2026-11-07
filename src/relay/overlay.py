"""The subtitle: a floating panel at the bottom of the screen."""

from dataclasses import astuple

from AppKit import (
    NSAttributedString,
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSLineBreakByWordWrapping,
    NSMakeRect,
    NSMutableAttributedString,
    NSMutableParagraphStyle,
    NSPanel,
    NSParagraphStyleAttributeName,
    NSScreen,
    NSStatusWindowLevel,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Quartz import CGColorCreateGenericGray

from relay.interpreter import Line
from relay.settings import Settings

START_WIDTH = 960
SCREEN_SHARE = 0.9
BOTTOM_MARGIN = 48
PADDING_X, PADDING_Y = 24, 14
CORNER_RADIUS = 14
ENGLISH_BRIGHTNESS = 0.78


def subtitle_rows(lines: list[Line], show_english: bool) -> list[tuple[str, bool]]:
    """Return each row's text and whether it is English. A failed translation appears once."""
    rows = []
    for line in lines:
        if show_english and line.english != line.chinese:
            rows.append((line.english, True))
        if line.chinese:
            rows.append((line.chinese, False))
    return rows


def styled(rows: list[tuple[str, bool]], settings: Settings) -> NSMutableAttributedString:
    paragraph = NSMutableParagraphStyle.alloc().init()
    paragraph.setAlignment_(NSTextAlignmentCenter)
    paragraph.setLineSpacing_(2)
    english = {
        NSFontAttributeName: NSFont.systemFontOfSize_(settings.english_size),
        NSForegroundColorAttributeName: NSColor.colorWithWhite_alpha_(ENGLISH_BRIGHTNESS, 1),
        NSParagraphStyleAttributeName: paragraph,
    }
    chinese = {
        NSFontAttributeName: NSFont.systemFontOfSize_(settings.chinese_size),
        NSForegroundColorAttributeName: NSColor.whiteColor(),
        NSParagraphStyleAttributeName: paragraph,
    }
    text = NSMutableAttributedString.alloc().init()
    for index, (row, is_english) in enumerate(rows):
        ending = "" if index == len(rows) - 1 else "\n"
        text.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(
                row + ending, english if is_english else chinese
            )
        )
    return text


class Overlay:
    def __init__(self):
        # A nonactivating panel never takes focus from the meeting or video.
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, START_WIDTH, 80),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setOpaque_(False)
        self.panel.setHasShadow_(False)
        self.panel.setIgnoresMouseEvents_(True)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setLevel_(NSStatusWindowLevel)
        self.panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorIgnoresCycle
        )

        self.background = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, START_WIDTH, 80))
        self.background.setWantsLayer_(True)
        self.background.layer().setCornerRadius_(CORNER_RADIUS)
        self.panel.setContentView_(self.background)

        self.label = NSTextField.wrappingLabelWithString_("")
        self.label.cell().setLineBreakMode_(NSLineBreakByWordWrapping)
        self.background.addSubview_(self.label)
        self.shown = None

    def show(self, lines: list[Line], settings: Settings) -> None:
        rows = subtitle_rows(lines, settings.show_english)
        shown = (rows, astuple(settings))
        if shown == self.shown:
            return
        self.shown = shown
        if not rows:
            self.panel.orderOut_(None)
            return
        self.background.layer().setBackgroundColor_(
            CGColorCreateGenericGray(0.05, settings.opacity / 100)
        )
        self.label.setAttributedStringValue_(styled(rows, settings))
        self.place(settings)
        self.panel.orderFrontRegardless()

    def place(self, settings: Settings) -> None:
        """Fit the panel to the text, so short lines stay small and long ones wrap."""
        frame = NSScreen.mainScreen().visibleFrame()
        limit = min(settings.width, frame.size.width * SCREEN_SHARE) - PADDING_X * 2
        size = self.label.cell().cellSizeForBounds_(NSMakeRect(0, 0, limit, 10_000))
        width = min(limit, size.width + 2) + PADDING_X * 2
        height = size.height + PADDING_Y * 2
        x = frame.origin.x + (frame.size.width - width) / 2
        room = max(0, frame.size.height - height - BOTTOM_MARGIN * 2)
        y = frame.origin.y + BOTTOM_MARGIN + room * settings.position / 100
        self.panel.setFrame_display_(NSMakeRect(x, y, width, height), True)
        self.label.setFrame_(NSMakeRect(PADDING_X, PADDING_Y, width - PADDING_X * 2, size.height))
