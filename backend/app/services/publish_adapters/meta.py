"""Stubs Meta (Facebook/Instagram) — asistido hasta OAuth Graph."""
from __future__ import annotations

from uuid import uuid4

from app.services.publish_adapters.base import AdapterResult, PublishAdapter


class MetaAdapter(PublishAdapter):
    def __init__(self, channel: str):
        self.channel = channel

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
        if not access_token or not external_account_id:
            return AdapterResult(
                ok=False,
                mode="assisted_required",
                message=f"{self.channel}: conecta Page/IG con token Graph o usa modo asistido",
            )
        if not live:
            fake = f"dry-run-meta-{uuid4().hex[:10]}"
            return AdapterResult(
                ok=True,
                mode="native_dry_run",
                external_post_id=fake,
                external_url=f"https://facebook.com/{fake}",
                message=f"Dry-run {self.channel} OK (Graph live pendiente de habilitar)",
                raw={"page_or_ig": external_account_id, "media": len(media_urls or [])},
            )
        return AdapterResult(
            ok=False,
            mode="unsupported",
            message=(
                f"{self.channel} live aún no implementado en este sprint "
                "(usa dry-run o asistido). Orden plan: LinkedIn → Meta."
            ),
        )
