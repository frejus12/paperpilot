from types import SimpleNamespace

import pytest

from paperpilot import llm


def test_complete_sends_prompts_and_returns_text(monkeypatch):
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="text", text="Standalone "),
                    SimpleNamespace(type="text", text="question"),
                ]
            )

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(llm, "_client", FakeClient())

    result = llm.complete("System instructions", "User question", max_tokens=80)

    assert result == "Standalone question"
    assert calls["model"] == llm.settings.llm_model
    assert calls["max_tokens"] == 80
    assert calls["system"] == "System instructions"
    assert calls["messages"] == [{"role": "user", "content": "User question"}]


def test_complete_raises_when_response_has_no_text(monkeypatch):
    class FakeMessages:
        def create(self, **kwargs):
            return SimpleNamespace(content=[])

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(llm, "_client", FakeClient())

    with pytest.raises(RuntimeError, match="The language model returned no text\\."):
        llm.complete("System instructions", "User question")
