"""Adaptador LinkedIn (UGC Posts API)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from uuid import uuid4

from app.services.publish_adapters.base import AdapterResult, PublishAdapter


class LinkedInAdapter(PublishAdapter):
    channel = "linkedin"

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
                message="LinkedIn sin access_token: usa modo asistido o conecta la cuenta",
            )
        author = external_account_id
        if author and not author.startswith("urn:"):
            author = f"urn:li:person:{author}"
        if not author:
            return AdapterResult(
                ok=False,
                mode="assisted_required",
                message="Falta external_account_id (urn:li:person:… o member id)",
            )

        text = (body_text or headline or "").strip()
        if not text:
            return AdapterResult(ok=False, mode="assisted_required", message="Copy vacío")

        if not live:
            fake_id = f"dry-run-li-{uuid4().hex[:12]}"
            return AdapterResult(
                ok=True,
                mode="native_dry_run",
                external_post_id=fake_id,
                external_url=f"https://www.linkedin.com/feed/update/{fake_id}",
                message="Dry-run LinkedIn OK (PUBLISH_NATIVE_LIVE=false). No se envió a la API.",
                raw={"author": author, "chars": len(text), "media_count": len(media_urls or [])},
            )

        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        req = urllib.request.Request(
            "https://api.linkedin.com/v2/ugcPosts",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body) if body else {}
                post_id = data.get("id") or resp.headers.get("x-restli-id") or "unknown"
                return AdapterResult(
                    ok=True,
                    mode="native_live",
                    external_post_id=str(post_id),
                    external_url=f"https://www.linkedin.com/feed/update/{post_id}",
                    message="Publicado en LinkedIn",
                    raw=data if isinstance(data, dict) else {"body": body},
                )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            return AdapterResult(
                ok=False,
                mode="native_live",
                message=f"LinkedIn API {exc.code}: {detail}",
                raw={"status": exc.code},
            )
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(
                ok=False,
                mode="native_live",
                message=f"LinkedIn error: {exc}",
            )
