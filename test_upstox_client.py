import pytest

from upstox_client import UpstoxClient


def test_missing_access_token():
    with pytest.raises(ValueError):
        UpstoxClient(access_token="")


def test_rejects_external_url():
    client = UpstoxClient(access_token="test-token")

    with pytest.raises(ValueError):
        client.get("https://example.com/api")

    client.close()


def test_rejects_invalid_endpoint():
    client = UpstoxClient(access_token="test-token")

    with pytest.raises(ValueError):
        client.get("user/profile")

    client.close()


def test_rejects_double_slash_endpoint():
    client = UpstoxClient(access_token="test-token")

    with pytest.raises(ValueError):
        client.get("//example.com")

    client.close()
  
