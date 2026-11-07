# Design

## Pipeline

Computer audio or microphone → local streaming speech recognition → sentences →
DeepSeek → subtitle and transcript. It only goes from English to Chinese.

## Speech model

Qwen3-ASR 0.6B, 8-bit, the same build as Quoth, with the language fixed to English.
`evals/bench_stream.py` replayed 3 minutes of read-aloud clips on an M5 with 16 GB:

| Chunk | Window | Median per chunk | Slowest chunk | Share of real time | Peak GPU memory |
|---|---|---|---|---|---|
| 2 s | 30 s | 0.135 s | 0.587 s | 8% | 1.14 GB |
| 1 s | 30 s | 0.113 s | 0.383 s | 12% | 1.14 GB |
| 1 s | 15 s | 0.108 s | 0.284 s | 12% | 1.03 GB |
| 0.5 s | 15 s | 0.100 s | 0.281 s | 21% | 1.03 GB |

No chunk ran over its budget. 0.5 s chunks with a 30 s window use 24% of real time. The app
uses a 30 s window because the 15 s window turned "bottleneck" into "Bottom neck" where a
window ended.

## Sentences

Only `stable_text` is translated, so a sentence is not sent while the model may still
change it. The model can still respell stable text, which moves character positions, so
the segmenter counts words. A sentence ends at `.`, `?` or `!`, at a 0.8 s pause, or at
25 words, where it cuts after the last comma.

Silence never reaches the model, because speech models invent text from it. A pause also
ends the stream, which keeps its text from growing for as long as the session runs.

## Latency

`evals/bench_latency.py` plays synthesized speech through the real recognizer and DeepSeek at
real-time speed, so the end of each sentence is known exactly. Medians over 20 sentences,
from the end of the sentence, before any audio capture delay:

| Speech | English shown | Full Chinese, before | Full Chinese, now |
|---|---|---|---|
| Pause after the sentence, 222 wpm | 1.0 s | 2.0 s | 1.8 s |
| Continuous, 202 wpm | 1.4 s | 3.2 s | 2.4 s |
| Continuous, 222 wpm | 1.4 s | 2.8 s | 2.3 s |
| Continuous, 275 wpm | 1.2 s | 2.8 s | 2.0 s |
| Continuous, 335 wpm | 1.3 s | 2.5 s | 2.1 s |

Before is a 1 s pause, 1 s chunks and 5 rollback words. Now is 0.8 s, 0.5 s and 3 words.
Delay does not grow with speed. One sentence at 202 wpm took 6.6 s, and the cause is unknown.

Synthesized speech hides the cost of going faster, so the settings were chosen on the 10
human clips. Recognizing them with each setting:

| Pause | Chunk | Rollback | WER | Pieces | Pieces of 1 or 2 words |
|---|---|---|---|---|---|
| 1 s | 1 s | 5 | 9.0% | 23 | 1 |
| 0.8 s | 0.5 s | 3 | 9.4% | 25 | 1 |
| 0.7 s | 0.5 s | 3 | 9.4% | 27 | 2 |
| 0.5 s | 0.5 s | 2 | 11.5% | 33 | 5 |

A 0.5 s pause scored the same as the others on synthesized speech, but on human speech it cut
sentences at normal pauses, which also breaks up what the recognizer can hear. One speaker
and 10 clips is a small sample.

## Translation

`deepseek-flash` with thinking disabled, streamed. Over 8 single sentences it took a median of 0.55 s
and at most 0.93 s. Each request carries the two sentences before it, so pronouns and
terms stay consistent, and that context also repaired recognition errors such as
"bottom neck".

One thread translates in order. When sentences queue up, they go out as one request, so
subtitles catch up instead of drifting behind. If the API fails or times out after
5 seconds, the English is shown and saved, so nothing said is lost.

## Computer audio

Core Audio taps have no Python binding, so `macos/audiotap.swift` captures a global tap and
writes 16 kHz mono audio to stdout. The sound keeps playing as normal.

macOS ties this permission to the app. From a shell inside VS Code the tap starts without
an error and never delivers audio. The helper also gets no callbacks while the Mac is
silent, so no audio is not a sign of a problem, and only the microphone warns about it.

## Microphone

Stopping a PortAudio input stream deadlocked inside CoreAudio in Quoth, so the stream stays
open once it is used. macOS then shows its microphone indicator until Relay quits. All-zero
blocks are dropped because that is what macOS sends without permission, which lets the app
warn after 3 seconds.

## Threads

The main thread runs AppKit and polls state ten times a second. One worker loads the model
and does all recognition, because MLX work stays on the thread that loaded it. A second
worker makes the network calls.

## Subtitle

A nonactivating panel that ignores the mouse, so it never takes focus from a meeting. It
clears after 8 seconds without new text. Each sentence shows its English first and adds the
Chinese as it streams in, so the English appears about 0.7 s before the translation.

The Subtitle window changes the font sizes, width, background, height on screen, number of
sentences and whether English shows. It previews a sample while nothing is being said, and
saves to `~/Library/Application Support/Relay/settings.json`. A damaged file gives the defaults.

## Controls

A full menu bar hides new items behind the notch without telling anyone, which is what
happened on the development Mac. So the controls also live in a small floating window.

## Transcript

Each session is one Markdown file, created on the first sentence so an empty session
leaves nothing behind. Every sentence is appended and the file closed at once, so a crash
loses nothing already translated. Audio is never saved.

## App bundle

`macos/launcher.c` embeds Python, so permissions belong to Relay and not to Python, and it
uses the checkout's `.venv`. The bundle is ad-hoc signed, so permissions follow its hash:
Python changes keep them, but changes in `macos/` may not.
