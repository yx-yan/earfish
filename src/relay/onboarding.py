"""A setup window that shows which permissions are still missing."""

import os
from collections.abc import Callable
from dataclasses import dataclass

import rumps
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSColor,
    NSFont,
    NSImage,
    NSImageView,
    NSMakeRect,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
    NSWorkspace,
)
from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
from Foundation import NSObject, NSURL

SETTINGS = "x-apple.systempreferences:com.apple.preference.security?Privacy_"
NOT_DETERMINED = 0  # AVAuthorizationStatusNotDetermined
AUTHORIZED = 3  # AVAuthorizationStatusAuthorized

WIDTH = 460
ROW_HEIGHT = 62
HEADER_HEIGHT = 96
FOOTER_HEIGHT = 58
MARGIN = 24


def microphone_status() -> int:
    return AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)


def has_microphone() -> bool:
    return microphone_status() == AUTHORIZED


def has_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


@dataclass(frozen=True)
class Check:
    title: str
    detail: str
    done: Callable[[], bool]
    settings: str | None = None


# Computer Audio has no row: macOS has no public way to read that permission,
# and it asks by itself the first time the app listens.
CHECKS = (
    Check("Microphone", "Hears the room when the source is Microphone.", has_microphone, "Microphone"),
    Check("DeepSeek API key", "Goes in .env. Without it, subtitles stay in English.", has_key),
)


def incomplete(checks=CHECKS) -> bool:
    return not all(check.done() for check in checks)


def label(text: str, frame, font, color=None) -> NSTextField:
    field = NSTextField.labelWithString_(text)
    field.setFrame_(frame)
    field.setFont_(font)
    if color is not None:
        field.setTextColor_(color)
    return field


class Actions(NSObject):
    def openSettings_(self, sender):
        # An app only appears in Settings after it has asked once.
        if microphone_status() == NOT_DETERMINED:
            AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                AVMediaTypeAudio, lambda _: None
            )
            return
        url = NSURL.URLWithString_(SETTINGS + CHECKS[sender.tag()].settings)
        NSWorkspace.sharedWorkspace().openURL_(url)

    def close_(self, sender):
        sender.window().close()


class SetupWindow:
    def __init__(self):
        self.actions = Actions.alloc().init()
        self.rows = []
        self.timer = rumps.Timer(self.tick, 1)

        height = HEADER_HEIGHT + ROW_HEIGHT * len(CHECKS) + FOOTER_HEIGHT
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIDTH, height),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Relay Setup")
        self.window.setReleasedWhenClosed_(False)
        content = self.window.contentView()

        icon = NSImageView.alloc().initWithFrame_(NSMakeRect(MARGIN - 4, height - 76, 60, 60))
        icon.setImage_(NSApplication.sharedApplication().applicationIconImage())
        content.addSubview_(icon)
        content.addSubview_(label(
            "Set up Relay", NSMakeRect(MARGIN + 66, height - 46, 320, 26), NSFont.boldSystemFontOfSize_(20)
        ))
        self.summary = label(
            "", NSMakeRect(MARGIN + 66, height - 68, 340, 18), NSFont.systemFontOfSize_(13),
            NSColor.secondaryLabelColor(),
        )
        content.addSubview_(self.summary)

        for index, check in enumerate(CHECKS):
            y = height - HEADER_HEIGHT - ROW_HEIGHT * (index + 1)
            self.rows.append(self.add_row(content, check, index, y))

        done = NSButton.buttonWithTitle_target_action_("Done", self.actions, "close:")
        done.setFrame_(NSMakeRect(WIDTH - MARGIN - 84, 16, 84, 28))
        done.setKeyEquivalent_("\r")
        content.addSubview_(done)

    def add_row(self, content, check: Check, index: int, y: int):
        mark = NSImageView.alloc().initWithFrame_(NSMakeRect(MARGIN, y + 20, 22, 22))
        content.addSubview_(mark)
        content.addSubview_(label(
            check.title, NSMakeRect(MARGIN + 34, y + 32, 280, 18), NSFont.systemFontOfSize_weight_(13, 0.3)
        ))
        detail = label(
            check.detail, NSMakeRect(MARGIN + 34, y + 2, 248, 30), NSFont.systemFontOfSize_(11.5),
            NSColor.secondaryLabelColor(),
        )
        detail.setLineBreakMode_(0)  # NSLineBreakByWordWrapping
        detail.setMaximumNumberOfLines_(2)
        content.addSubview_(detail)

        button = None
        if check.settings:
            button = NSButton.buttonWithTitle_target_action_("Allow", self.actions, "openSettings:")
            button.setBezelStyle_(NSBezelStyleRounded)
            button.setTag_(index)
            button.setFrame_(NSMakeRect(WIDTH - MARGIN - 112, y + 16, 112, 28))
            content.addSubview_(button)
        return check, mark, button

    def show(self) -> None:
        self.refresh()
        self.window.center()
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)
        if not self.timer.is_alive():
            self.timer.start()

    def tick(self, _) -> None:
        """Poll, because macOS sends no event when a permission changes."""
        if self.window.isVisible():
            self.refresh()
        else:
            self.timer.stop()

    def refresh(self) -> None:
        remaining = 0
        for check, mark, button in self.rows:
            done = check.done()
            remaining += not done
            name = "checkmark.circle.fill" if done else "circle"
            mark.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, check.title))
            mark.setContentTintColor_(NSColor.systemGreenColor() if done else NSColor.tertiaryLabelColor())
            if button is not None:
                button.setHidden_(done)
        self.summary.setStringValue_(
            f"{remaining} left to turn on." if remaining else "All set. Press Start to get subtitles."
        )
