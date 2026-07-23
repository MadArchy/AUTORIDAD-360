"""Tests adaptadores nativos de publicación."""
from __future__ import annotations

from app.services.publish_adapters.linkedin import LinkedInAdapter
from app.services.publish_adapters.meta import MetaAdapter
from app.services.publish_adapters import get_adapter, supported_native_channels


def test_native_channels_registered():
    assert "linkedin" in supported_native_channels()
    assert "facebook" in supported_native_channels()
    assert get_adapter("linkedin") is not None
    assert get_adapter("blog") is None


def test_linkedin_assisted_without_token():
    result = LinkedInAdapter().publish(
        body_text="Hola",
        headline="T",
        access_token=None,
        external_account_id="urn:li:person:abc",
        live=False,
    )
    assert result.ok is False
    assert result.mode == "assisted_required"


def test_linkedin_dry_run_with_token():
    result = LinkedInAdapter().publish(
        body_text="Post de autoridad",
        headline="Titulo",
        access_token="test-token-xxxxxx",
        external_account_id="abc123",
        live=False,
    )
    assert result.ok is True
    assert result.mode == "native_dry_run"
    assert result.external_post_id


def test_meta_live_blocked():
    result = MetaAdapter("facebook").publish(
        body_text="x",
        headline=None,
        access_token="tok",
        external_account_id="page1",
        live=True,
    )
    assert result.ok is False
    assert result.mode == "unsupported"
