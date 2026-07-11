"""Tests for gallery URL helpers."""

from __future__ import annotations

from easypal_next.network import util


def test_preferred_gallery_url_uses_lan_when_available(monkeypatch):
    monkeypatch.setattr(util, "get_primary_lan_ip", lambda: "192.168.1.50")
    assert util.preferred_gallery_url(8765) == "http://192.168.1.50:8765"


def test_preferred_gallery_url_falls_back_to_localhost(monkeypatch):
    monkeypatch.setattr(util, "get_primary_lan_ip", lambda: None)
    assert util.preferred_gallery_url(8765) == "http://localhost:8765"
