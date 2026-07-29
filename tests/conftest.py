"""Shared fixtures: isolate every test from the real cache and query log."""

import pytest

import pretaverdi.client as client_module


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Redirect CACHE_DIR and QUERY_LOG_PATH so no test touches the repo's .cache/."""
    log_path = tmp_path / "query_log.jsonl"
    monkeypatch.setattr(client_module, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(client_module, "QUERY_LOG_PATH", log_path)
    client_module._get_session.cache_clear()
    yield log_path
