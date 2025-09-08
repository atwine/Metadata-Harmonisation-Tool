import streamlit as st
from dataclasses import dataclass, asdict


@dataclass
class _Counters:
    calls_total: int = 0
    chat_calls: int = 0
    embed_calls: int = 0
    success: int = 0
    errors: int = 0
    prompt_chars: int = 0
    completion_chars: int = 0

    def reset(self):
        self.calls_total = 0
        self.chat_calls = 0
        self.embed_calls = 0
        self.success = 0
        self.errors = 0
        self.prompt_chars = 0
        self.completion_chars = 0


class AIMonitor:
    """
    Minimal AI usage monitor (session-scoped via Streamlit).
    Tracks counts, approximate tokens, and success/failure stats.
    """
    def __init__(self):
        self.c = _Counters()

    # --- recording helpers ---
    def record_chat(self, prompt_chars: int, completion_chars: int, success: bool):
        self.c.calls_total += 1
        self.c.chat_calls += 1
        self.c.prompt_chars += max(0, int(prompt_chars or 0))
        self.c.completion_chars += max(0, int(completion_chars or 0))
        if success:
            self.c.success += 1
        else:
            self.c.errors += 1

    def record_embed(self, success: bool):
        self.c.calls_total += 1
        self.c.embed_calls += 1
        if success:
            self.c.success += 1
        else:
            self.c.errors += 1

    # --- derived metrics ---
    @property
    def prompt_tokens(self) -> int:
        # rough estimate: 1 token ≈ 4 chars
        return int(self.c.prompt_chars / 4) if self.c.prompt_chars else 0

    @property
    def completion_tokens(self) -> int:
        return int(self.c.completion_chars / 4) if self.c.completion_chars else 0

    @property
    def success_rate(self) -> float:
        total = self.c.success + self.c.errors
        return (100.0 * self.c.success / total) if total else 0.0

    def as_dict(self):
        d = asdict(self.c)
        d.update({
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'success_rate': round(self.success_rate, 2),
        })
        return d

    def reset(self):
        self.c.reset()


# --- session accessors ---

def get_ai_monitor() -> AIMonitor:
    if 'ai_monitor' not in st.session_state:
        st.session_state['ai_monitor'] = AIMonitor()
    return st.session_state['ai_monitor']
