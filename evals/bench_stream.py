"""Replay English clips through streaming ASR and check it keeps up with real time."""

import argparse
import time
from pathlib import Path

import mlx.core as mx
import numpy as np
from mlx_qwen3_asr import Session

SAMPLE_RATE = 16_000
MODEL = "moona3k/mlx-qwen3-asr-0.6b-8bit"


def load_clips(folder: Path, minutes: float) -> np.ndarray:
    import wave

    clips = []
    for path in sorted(folder.glob("en-*.wav")):
        with wave.open(str(path)) as f:
            samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
        clips += [samples.astype(np.float32) / 32768, np.zeros(SAMPLE_RATE // 2, np.float32)]
    audio = np.concatenate(clips)
    repeats = int(np.ceil(minutes * 60 * SAMPLE_RATE / len(audio)))
    return np.tile(audio, repeats)[: int(minutes * 60 * SAMPLE_RATE)]


def run(session: Session, audio: np.ndarray, chunk: float, context: float) -> None:
    state = session.init_streaming(
        language="English", chunk_size_sec=chunk, max_context_sec=context
    )
    step = int(chunk * SAMPLE_RATE)
    times, tails = [], []
    mx.reset_peak_memory()
    for start in range(0, len(audio), step):
        began = time.perf_counter()
        state = session.feed_audio(audio[start : start + step], state)
        times.append(time.perf_counter() - began)
        tails.append(len(state.text.split()) - len(state.stable_text.split()))
    times = np.array(times)
    print(
        f"chunk {chunk:.1f}s context {context:.0f}s | "
        f"median {np.median(times):.3f}s p95 {np.percentile(times, 95):.3f}s max {times.max():.3f}s | "
        f"load {times.sum() / (len(audio) / SAMPLE_RATE):.2f} of real time | "
        f"over budget {np.mean(times > chunk):.1%} | "
        f"unstable words median {np.median(tails):.0f} | "
        f"peak GPU {mx.get_peak_memory() / 2**30:.2f} GB"
    )
    print("  stable tail:", state.stable_text[-120:])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("samples", type=Path)
    parser.add_argument("--minutes", type=float, default=3)
    args = parser.parse_args()
    audio = load_clips(args.samples, args.minutes)
    session = Session(model=MODEL)
    for chunk, context in [(2, 30), (1, 30), (1, 15), (0.5, 30), (0.5, 15)]:
        run(session, audio, chunk, context)
