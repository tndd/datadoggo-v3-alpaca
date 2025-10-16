"""Settingsモジュールの基本挙動を検証する."""

from datadoggo_v3_alpaca.config import Settings


def test_database_url_falls_back_to_test(monkeypatch) -> None:
    """ENVIRONMENT未指定でもTESTのDSNが利用されることを確認する."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql://user:pass@localhost:5432/test_db")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url == "postgresql://user:pass@localhost:5432/test_db"


def test_environment_switch(monkeypatch) -> None:
    """ENVIRONMENT指定で接続先が切り替わる."""
    monkeypatch.setenv("ENVIRONMENT", "stg")
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql://user:pass@localhost:5432/test_db")
    monkeypatch.setenv("DATABASE_URL_STG", "postgresql://user:pass@localhost:5432/stg_db")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url.endswith("stg_db")
