"""Stub TikTok Content Posting API."""
from __future__ import annotations

from uuid import uuid4

from app.services.publish_adapters.base import AdapterResult, PublishAdapter


class TikTokAdapter(PublishAdapter):
    channel = "tiktok"

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
        if not access_token:
            return AdapterResult(
                ok=False,
                mode="assisted_required",
                message="TikTok: token + video 9:16; usa asistido por ahora",
            )
        if not live:
            fake = f"dry-run-tt-{uuid4().hex[:10]}"
            return AdapterResult(
                ok=True,
                mode="native_dry_run",
                external_post_id=fake,
                external_url=f"https://www.tiktok.com/@user/video/{fake}",
                message="Dry-run TikTok OK (posting live pendiente)",
            )
        return AdapterResult(
            ok=False,
            mode="unsupported",
            message="TikTok live posting no implementado aún",
        )
