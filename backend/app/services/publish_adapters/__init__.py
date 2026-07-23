"""Registro de adaptadores por canal."""
from __future__ import annotations

from app.services.publish_adapters.base import PublishAdapter
from app.services.publish_adapters.linkedin import LinkedInAdapter
from app.services.publish_adapters.meta import MetaAdapter
from app.services.publish_adapters.tiktok import TikTokAdapter
from app.services.publish_adapters.youtube import YouTubeAdapter

_ADAPTERS: dict[str, PublishAdapter] = {
    "linkedin": LinkedInAdapter(),
    "facebook": MetaAdapter("facebook"),
    "instagram": MetaAdapter("instagram"),
    "youtube": YouTubeAdapter(),
    "tiktok": TikTokAdapter(),
}


def get_adapter(channel: str) -> PublishAdapter | None:
    return _ADAPTERS.get(channel)


def supported_native_channels() -> list[str]:
    return sorted(_ADAPTERS.keys())
