import pytest

MOCK_URL = "https://test.com/"


@pytest.fixture(autouse=True)
def set_test_env_vars(monkeypatch):
    monkeypatch.setenv("URL", MOCK_URL)
