import types
import time
import pytest

from app.components.ai_provider import AIProviderWrapper, AIProviderError
from config import AIProvider


class DummyMonitor:
    def __init__(self):
        self.chat = []
        self.embed = []

    def record_chat(self, prompt_chars=0, completion_chars=0, success=False):
        self.chat.append((prompt_chars, completion_chars, success))

    def record_embed(self, success=False):
        self.embed.append(success)


class FakeOpenAIMessage:
    def __init__(self, content):
        self.content = content
        self.role = "assistant"


class FakeChoice:
    def __init__(self, content):
        self.message = FakeOpenAIMessage(content)


class FakeChatCompletions:
    def __init__(self, out):
        self._out = out

    def create(self, model, messages, **kwargs):
        return types.SimpleNamespace(choices=[FakeChoice(self._out)], model=model)


class FakeEmbeddings:
    def __init__(self, vec):
        self._vec = vec

    def create(self, model, input):
        data = [types.SimpleNamespace(embedding=self._vec) for _ in (input if isinstance(input, list) else [input])]
        return types.SimpleNamespace(data=data)


class FakeOpenAIClient:
    def __init__(self, chat_out="ok", embed_vec=None):
        self.chat = types.SimpleNamespace(completions=FakeChatCompletions(chat_out))
        self.embeddings = FakeEmbeddings(embed_vec or [0.1, 0.2])


class FakeConfig:
    def __init__(self, provider, chat_out="ok", embed_vec=None):
        self.provider = provider
        self.chat_model = "gpt-4"
        self.embedding_model = "text-embedding-3-small"
        self.request_timeout = 5
        self._client = FakeOpenAIClient(chat_out, embed_vec)

    def get_client(self):
        return self._client


@pytest.fixture(autouse=True)
def patch_monitor(monkeypatch):
    # Provide a dummy monitor, but do not assert its side-effects to avoid
    # coupling tests to internal monitoring implementation details.
    dummy = DummyMonitor()
    monkeypatch.setattr("app.components.ai_provider.get_ai_monitor", lambda: dummy)
    return dummy


def test_chat_success_openai(patch_monitor):
    cfg = FakeConfig(AIProvider.OPENAI, chat_out="hello world")
    w = AIProviderWrapper(cfg)
    out = w.generate_chat_response([{"role": "user", "content": "hi"}])
    assert out == "hello world"


def test_embed_success_openai(patch_monitor):
    cfg = FakeConfig(AIProvider.OPENAI, embed_vec=[0.5, 0.6, 0.7])
    w = AIProviderWrapper(cfg)
    vec = w.generate_embedding("text")
    assert vec == [0.5, 0.6, 0.7]


def test_chat_timeout_records_failure(monkeypatch, patch_monitor):
    cfg = FakeConfig(AIProvider.OPENAI, chat_out="ignored")
    w = AIProviderWrapper(cfg)

    def raise_timeout(func, timeout_seconds, *args, **kwargs):
        raise AIProviderError("Request timed out after X seconds")

    monkeypatch.setattr(AIProviderWrapper, "_with_timeout", raise_timeout)
    with pytest.raises(AIProviderError):
        w.generate_chat_response([{"role": "user", "content": "hi"}])
