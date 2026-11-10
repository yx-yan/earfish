"""A small window with the controls, because a full menu bar hides new items behind the notch."""

from AppKit import (
    NSBackingStoreBuffered,
    NSButton,
    NSFloatingWindowLevel,
    NSFont,
    NSMakeRect,
    NSObject,
    NSPanel,
    NSScreen,
    NSSegmentedControl,
    NSSegmentSwitchTrackingSelectOne,
    NSTextField,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskUtilityWindow,
)

WIDTH, HEIGHT = 300, 112
MARGIN = 16
BUTTON_HEIGHT = 28
TOP_MARGIN = 12


class Target(NSObject):
    """AppKit buttons need an Objective-C object to call."""

    def toggle_(self, _):
        self.on_toggle()

    def source_(self, sender):
        self.on_source(self.names[sender.selectedSegment()])

    def subtitle_(self, _):
        self.on_subtitle()

    def transcripts_(self, _):
        self.on_transcripts()

    def quit_(self, _):
        self.on_quit()


class Controls:
    def __init__(self, names, chosen, on_toggle, on_source, on_subtitle, on_transcripts, on_quit):
        self.target = Target.alloc().init()
        self.target.names = names
        self.target.on_toggle = on_toggle
        self.target.on_source = on_source
        self.target.on_subtitle = on_subtitle
        self.target.on_transcripts = on_transcripts
        self.target.on_quit = on_quit

        # A nonactivating panel takes clicks without pulling focus from the meeting.
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, WIDTH, HEIGHT),
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskUtilityWindow
            | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setTitle_("Earfish")
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setMovableByWindowBackground_(True)
        self.panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        content = self.panel.contentView()
        inner = WIDTH - MARGIN * 2

        self.status = NSTextField.labelWithString_("")
        self.status.setFont_(NSFont.systemFontOfSize_(12))
        self.status.setFrame_(NSMakeRect(MARGIN, 84, inner, 18))
        content.addSubview_(self.status)

        self.sources = NSSegmentedControl.segmentedControlWithLabels_trackingMode_target_action_(
            names, NSSegmentSwitchTrackingSelectOne, self.target, "source:"
        )
        self.sources.setFrame_(NSMakeRect(MARGIN, 48, inner, BUTTON_HEIGHT))
        self.sources.setSelectedSegment_(names.index(chosen))
        content.addSubview_(self.sources)

        self.toggle = self.button("Start", "toggle:", MARGIN, 60)
        self.button("Subtitle", "subtitle:", MARGIN + 64, 68)
        self.button("Transcripts", "transcripts:", MARGIN + 136, 86)
        self.button("Quit", "quit:", MARGIN + 226, 42)
        self.toggle.setKeyEquivalent_("")

    def button(self, title: str, action: str, x: int, width: int) -> NSButton:
        button = NSButton.buttonWithTitle_target_action_(title, self.target, action)
        button.setFrame_(NSMakeRect(x, 10, width, BUTTON_HEIGHT))
        self.panel.contentView().addSubview_(button)
        return button

    def show(self) -> None:
        frame = NSScreen.mainScreen().visibleFrame()
        x = frame.origin.x + frame.size.width - WIDTH - MARGIN
        y = frame.origin.y + frame.size.height - TOP_MARGIN
        self.panel.setFrameTopLeftPoint_((x, y))
        self.panel.orderFrontRegardless()

    def update(self, status: str, toggle: str, enabled: bool) -> None:
        if self.status.stringValue() != status:
            self.status.setStringValue_(status)
        if self.toggle.title() != toggle:
            self.toggle.setTitle_(toggle)
        self.toggle.setEnabled_(enabled)
