"""Translate English sentences into Chinese with DeepSeek."""

import os
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI, OpenAIError

PROMPT = (Path(__file__).parent / "prompts" / "translate.md").read_text()
CONTEXT_SENTENCES = 2


@dataclass
class Translation:
    text: str
    fell_back: bool = False


class Translator:
    def __init__(self, client: OpenAI | None = None, model: str = "deepseek-flash", timeout: float = 5):
        self.client = client or OpenAI(
            # A missing key fails on the first call, which falls back to the English.
            api_key=os.environ.get("DEEPSEEK_API_KEY") or "missing",
            base_url="https://api.deepseek.com",
            max_retries=0,
        )
        self.model = model
        self.timeout = timeout
        self.earlier = deque(maxlen=CONTEXT_SENTENCES)

    def translate(self, english: str, on_text: Callable[[str], None] = lambda _: None) -> Translation:
        """Return the Chinese, or the English if the API fails, so nothing said is lost."""
        request = f"Translate:\n{english}"
        if self.earlier:
            request = "Earlier:\n" + "\n".join(self.earlier) + f"\n\n{request}"
        text = ""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": request},
                ],
                temperature=0,
                timeout=self.timeout,
                stream=True,
                extra_body={"thinking": {"type": "disabled"}},
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text += chunk.choices[0].delta.content
                    on_text(text)
        except OpenAIError:
            return Translation(english, fell_back=True)
        self.earlier.append(english)
        text = text.strip()
        return Translation(text) if text else Translation(english, fell_back=True)
