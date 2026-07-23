"""Resultado común de adaptadores de publicación nativa."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterResult:
    ok: bool
    mode: str  # native_live | native_dry_run | assisted_required | unsupported
    external_post_id: str | None = None
    external_url: str | None = None
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class PublishAdapter:
    channel: str = ""

    def publish(
        self,
        *,
        body_text: str,
        headline: str | None,
        access_token: str | None,
        external_account_id: str | None,
        live: bool,
        media_urls: list[str] | None = None,
    ) -> AdapterResult:
        raise NotImplementedError
