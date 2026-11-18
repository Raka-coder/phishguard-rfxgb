"""Isolasi tes: Layer 0 Google dimatikan kecuali tes yang eksplisit menyalakannya."""

import pytest

from src import config as cfg


@pytest.fixture(autouse=True)
def _offline_google(monkeypatch):
    monkeypatch.setattr(cfg, "USE_GOOGLE", False)
    monkeypatch.setattr(cfg, "GOOGLE_API_KEY", "")
