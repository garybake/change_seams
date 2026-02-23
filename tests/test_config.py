"""Tests for Seam 4: runtime config parsing."""
import os
import pytest


def test_enabled_tools_parsed_from_comma_string(monkeypatch):
    monkeypatch.setenv("ENABLED_TOOLS", "echo,weather,search")
    # Re-create Settings with the patched env
    from pydantic_settings import BaseSettings
    from app.config import Settings

    s = Settings()
    assert s.enabled_tools == ["echo", "weather", "search"]


def test_enabled_tools_strips_whitespace(monkeypatch):
    monkeypatch.setenv("ENABLED_TOOLS", " echo , weather ")
    from app.config import Settings

    s = Settings()
    assert s.enabled_tools == ["echo", "weather"]


def test_enabled_tools_single_value(monkeypatch):
    monkeypatch.setenv("ENABLED_TOOLS", "echo")
    from app.config import Settings

    s = Settings()
    assert s.enabled_tools == ["echo"]


def test_get_llm_returns_chat_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from importlib import reload
    import app.config as cfg_mod
    import app.providers.llm as llm_mod

    reload(cfg_mod)
    reload(llm_mod)

    from langchain_openai import ChatOpenAI

    llm = llm_mod.get_llm()
    assert isinstance(llm, ChatOpenAI)


def test_get_llm_raises_for_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake-provider")
    from importlib import reload
    import app.config as cfg_mod
    import app.providers.llm as llm_mod

    reload(cfg_mod)
    reload(llm_mod)

    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        llm_mod.get_llm()
