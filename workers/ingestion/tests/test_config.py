import pytest

from src.config import require_env


class Env:
    AIRTABLE_API_TOKEN = "token-from-object"


def test_require_env_reads_object_attribute():
    assert require_env(Env(), "AIRTABLE_API_TOKEN") == "token-from-object"


def test_require_env_raises_for_missing_key():
    with pytest.raises(ValueError, match="AIRTABLE_API_TOKEN"):
        require_env({}, "AIRTABLE_API_TOKEN")
