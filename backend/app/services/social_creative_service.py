"""Creatividades de publicidad para carrusel y redes (OpenAI Images + Pillow)."""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_providers import AIProvider
from app.models.content import ContentPiece
from app.models.publishing import MediaAsset
from app.services.crypto_keys import decrypt_secret

logger = logging.getLogger(__name__)

# backend/media → servido en /media
MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"

RATIOS: dict[str, tuple[int, int]] = {
    "4:5": (1080, 1350),
    "1:1": (1080, 1080),
    "1.91:1": (1200, 628),
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _openai_api_key(db: Session) -> str | None:
    providers = (
        db.query(AIProvider)
        .filter(AIProvider.is_active.is_(True), AIProvider.provider_type == "openai")
        .order_by(AIProvider.priority.asc())
        .all()
    )
    for p in providers:
        if p.encrypted_api_key:
            try:
                key = decrypt_secret(p.encrypted_api_key)
                if key and key.strip():
                    return key.strip()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Cannot decrypt OpenAI key for provider %s: %s", p.id, exc)
    env = (os.getenv("OPENAI_API_KEY") or "").strip()
    return env or None


def try_openai_image(db: Session, prompt: str, *, size: str = "1024x1024") -> bytes | None:
    """Genera una imagen con OpenAI Images; None si no hay key o falla."""
    api_key = _openai_api_key(db)
    if not api_key:
        return None
    payload = {
        "model": "dall-e-3",
        "prompt": prompt[:3800],
        "n": 1,
        "size": size if size in {"1024x1024", "1024x1792", "1792x1024"} else "1024x1024",
        "response_format": "b64_json",
        "quality": "standard",
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        b64 = (data.get("data") or [{}])[0].get("b64_json")
        if not b64:
            return None
        return base64.b64decode(b64)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        logger.warning("OpenAI Images HTTP %s: %s", exc.code, body)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("OpenAI Images failed: %s", exc)
        return None


def _load_font(size: int):
    from PIL import ImageFont

    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def render_brand_slide(
    title: str,
    body: str,
    *,
    ratio: str = "4:5",
    bg_bytes: bytes | None = None,
    footer: str = "Autoridad 360",
    slide_label: str | None = None,
) -> bytes:
    """PNG tipográfico de marca; opcionalmente sobre fondo IA."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    width, height = RATIOS.get(ratio, RATIOS["4:5"])
    if bg_bytes:
        try:
            bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
            bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            bg = ImageEnhance.Brightness(bg).enhance(0.45)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=1.2))
        except Exception:  # noqa: BLE001
            bg = Image.new("RGB", (width, height), (15, 23, 42))
    else:
        bg = Image.new("RGB", (width, height), (15, 23, 42))
        draw_grad = ImageDraw.Draw(bg)
        for y in range(height):
            t = y / max(height - 1, 1)
            r = int(15 + (30 - 15) * t)
            g = int(23 + (41 - 23) * t)
            b = int(42 + (59 - 42) * t)
            draw_grad.line([(0, y), (width, y)], fill=(r, g, b))

    # Overlay panel
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    margin = int(width * 0.07)
    panel_top = int(height * 0.18)
    panel_bottom = int(height * 0.88)
    od.rounded_rectangle(
        [margin, panel_top, width - margin, panel_bottom],
        radius=28,
        fill=(15, 23, 42, 200),
    )
    composed = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(composed)

    title_font = _load_font(54 if width >= 1000 else 36)
    body_font = _load_font(34 if width >= 1000 else 24)
    meta_font = _load_font(22)
    footer_font = _load_font(20)

    x = margin + 36
    y = panel_top + 40
    max_chars_title = 28 if width >= 1000 else 22
    max_chars_body = 38 if width >= 1000 else 30

    if slide_label:
        draw.text((x, y), slide_label.upper(), fill=(56, 189, 248), font=meta_font)
        y += 36

    for line in textwrap.wrap((title or "Sin título").strip(), width=max_chars_title)[:4]:
        draw.text((x, y), line, fill=(255, 255, 255), font=title_font)
        y += 62

    y += 16
    for line in textwrap.wrap((body or "").strip(), width=max_chars_body)[:10]:
        draw.text((x, y), line, fill=(226, 232, 240), font=body_font)
        y += 42

    draw.text(
        (x, height - margin - 40),
        footer,
        fill=(148, 163, 184),
        font=footer_font,
    )

    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_slide_prompt(title: str, body: str, *, theme_hint: str = "") -> str:
    topic = f"{title}. {body}".strip()[:500]
    return (
        "Professional editorial social media background for a legal-tech authority brand. "
        "Dark slate navy atmosphere, subtle abstract geometry, soft cyan accent light, "
        "no text, no logos, no watermarks, no faces, no stock-photo people. "
        f"Theme: {theme_hint or 'AI governance and corporate law'}. "
        f"Concept inspired by: {topic}"
    )


def _slides_from_piece(piece: ContentPiece) -> list[dict[str, Any]]:
    data = piece.body_json if isinstance(piece.body_json, dict) else {}
    slides = data.get("slides") if isinstance(data.get("slides"), list) else None
    if slides:
        out = []
        for i, s in enumerate(slides):
            if isinstance(s, dict):
                out.append(
                    {
                        "title": (s.get("title") or f"Slide {i + 1}")[:180],
                        "content": (s.get("content") or s.get("text") or "")[:600],
                        **{k: v for k, v in s.items() if k not in ("title", "content", "text")},
                    }
                )
            else:
                out.append({"title": f"Slide {i + 1}", "content": str(s)[:600]})
        return out[:8]
    # Cover único desde texto
    return [
        {
            "title": (piece.title or "Publicación")[:180],
            "content": (piece.body_text or "")[:500],
        }
    ]


def _channel_ratio(format_type: str) -> str:
    if format_type == "carousel":
        return "4:5"
    if format_type == "newsletter":
        return "1.91:1"
    if format_type == "video_script":
        return "9:16"
    return "4:5"


def generate_creatives_for_piece(
    db: Session,
    piece: ContentPiece,
    *,
    organization_id: int,
    use_openai: bool = True,
) -> dict[str, Any]:
    """Genera PNGs por slide/cover, MediaAssets, y actualiza body_json de la pieza."""
    ratio = _channel_ratio(piece.format_type)
    # dall-e-3 portrait closest
    openai_size = "1024x1792" if ratio in {"4:5", "9:16"} else "1024x1024"
    if ratio == "1.91:1":
        openai_size = "1792x1024"

    slides = _slides_from_piece(piece)
    rel_dir = Path(str(organization_id)) / str(piece.id)
    abs_dir = MEDIA_ROOT / rel_dir
    _ensure_dir(abs_dir)

    assets: list[MediaAsset] = []
    updated_slides: list[dict[str, Any]] = []
    used_openai = False
    engine_bits: list[str] = []

    width, height = RATIOS.get(ratio, RATIOS["4:5"])

    for idx, slide in enumerate(slides):
        title = slide.get("title") or f"Slide {idx + 1}"
        body = slide.get("content") or ""
        bg = None
        if use_openai:
            prompt = build_slide_prompt(title, body, theme_hint=piece.title or "")
            bg = try_openai_image(db, prompt, size=openai_size)
            if bg:
                used_openai = True

        png = render_brand_slide(
            title,
            body,
            ratio=ratio if ratio in RATIOS else "4:5",
            bg_bytes=bg,
            slide_label=f"{idx + 1} / {len(slides)}" if len(slides) > 1 else None,
        )
        filename = f"slide_{idx + 1:02d}.png"
        abs_path = abs_dir / filename
        abs_path.write_bytes(png)
        storage_url = f"/media/{rel_dir.as_posix()}/{filename}"

        asset = MediaAsset(
            organization_id=organization_id,
            kind="image",
            title=f"{piece.format_type} · {title}"[:256],
            storage_url=storage_url,
            mime_type="image/png",
            width=width,
            height=height,
            aspect_ratio=ratio if ratio in {"1:1", "4:5", "9:16", "16:9"} else "4:5",
            alt_text=f"{title}: {body}"[:512],
            status="ready",
            meta_json={
                "piece_id": piece.id,
                "slide_index": idx,
                "openai_bg": bool(bg),
                "generated_at": _utcnow_iso(),
            },
        )
        db.add(asset)
        db.flush()
        assets.append(asset)

        updated = dict(slide)
        updated["title"] = title
        updated["content"] = body
        updated["image_url"] = storage_url
        updated["media_asset_id"] = asset.id
        updated_slides.append(updated)

    engine = "openai+brand" if used_openai else "brand_only"
    engine_bits.append(engine)

    body_json = dict(piece.body_json) if isinstance(piece.body_json, dict) else {}
    if piece.format_type == "carousel":
        body_json["format"] = "carousel"
        body_json["slides"] = updated_slides
    else:
        body_json["creatives"] = {
            "covers": [
                {
                    "image_url": s["image_url"],
                    "media_asset_id": s["media_asset_id"],
                    "title": s.get("title"),
                }
                for s in updated_slides
            ]
        }
        if updated_slides:
            body_json["image_url"] = updated_slides[0]["image_url"]
            body_json["media_asset_id"] = updated_slides[0]["media_asset_id"]

    piece.body_json = body_json
    gen = dict(piece.generation_json) if isinstance(piece.generation_json, dict) else {}
    gen["creatives"] = {
        "engine": engine,
        "asset_ids": [a.id for a in assets],
        "generated_at": _utcnow_iso(),
        "ratio": ratio,
    }
    piece.generation_json = gen
    db.commit()
    db.refresh(piece)

    return {
        "piece_id": piece.id,
        "engine": engine,
        "ratio": ratio,
        "asset_ids": [a.id for a in assets],
        "assets": [
            {
                "id": a.id,
                "title": a.title,
                "storage_url": a.storage_url,
                "width": a.width,
                "height": a.height,
                "aspect_ratio": a.aspect_ratio,
            }
            for a in assets
        ],
        "slides": updated_slides if piece.format_type == "carousel" else None,
        "image_url": (updated_slides[0]["image_url"] if updated_slides else None),
    }
