"""R2 settings alias resolution (arthor-ai env names)."""

from __future__ import annotations

import pytest


def test_r2_arthor_ai_aliases_resolve(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for var in (
        "R2_ENDPOINT_URL",
        "R2_BUCKET",
        "R2_ACCOUNT_ID",
        "R2_BUCKET_NAME",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_PUBLIC_URL",
    ):
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setenv("R2_ACCOUNT_ID", "abc123account")
    monkeypatch.setenv("R2_BUCKET_NAME", "my-artifacts")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://pub.example.r2.dev")

    from app.config import Settings

    s = Settings()
    assert s.r2_endpoint_url == "https://abc123account.r2.cloudflarestorage.com"
    assert s.r2_bucket == "my-artifacts"
    assert s.r2_public_url == "https://pub.example.r2.dev"


def test_r2_canonical_names_take_precedence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://custom.endpoint")
    monkeypatch.setenv("R2_BUCKET", "canonical-bucket")
    monkeypatch.setenv("R2_ACCOUNT_ID", "ignored")
    monkeypatch.setenv("R2_BUCKET_NAME", "ignored-name")

    from app.config import Settings

    s = Settings()
    assert s.r2_endpoint_url == "https://custom.endpoint"
    assert s.r2_bucket == "canonical-bucket"
