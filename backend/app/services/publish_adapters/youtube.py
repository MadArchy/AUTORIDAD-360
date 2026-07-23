"""Stub YouTube Data API."""
from __future__ import annotations

from uuid import uuid4

from app.services.publish_adapters.base import AdapterResult, PublishAdapter


class YouTubeAdapter(PublishAdapter):
    channel = "youtube"

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
                message="YouTube: OAuth + video file requerido; usa asistido por ahora",
            )
        if not live:
            fake = f"dry-run-yt-{uuid4().hex[:10]}"
            return AdapterResult(
                ok=True,
                mode="native_dry_run",
                external_post_id=fake,
                external_url=f"https://youtube.com/watch?v={fake}",
                message="Dry-run YouTube OK (upload live pendiente)",
                raw={"title": (headline or "")[:90]},
            )
        return AdapterResult(
            ok=False,
            mode="unsupported",
            message="YouTube live upload no implementado aún",
        )
