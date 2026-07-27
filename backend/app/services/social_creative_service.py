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
from app.services.crypto_keys import decrypt_secret_with_rotation, encrypt_secret

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
                key, needs_reencrypt = decrypt_secret_with_rotation(p.encrypted_api_key)
                if needs_reencrypt:
                    p.encrypted_api_key = encrypt_secret(key)
                    db.add(p)
                    db.commit()
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

    # gpt-image-1 (cuentas actuales) + fallback dall-e-3 (cuentas legacy).
    size_map = {
        "1024x1024": "1024x1024",
        "1024x1792": "1024x1536",
        "1792x1024": "1536x1024",
        "1024x1536": "1024x1536",
        "1536x1024": "1536x1024",
    }
    resolved = size_map.get(size, "1024x1024")

    payloads = [
        {
            "model": "gpt-image-1",
            "prompt": prompt[:3800],
            "n": 1,
            "size": resolved,
            "quality": "high",
        },
        {
            "model": "gpt-image-1",
            "prompt": prompt[:3800],
            "n": 1,
            "size": resolved,
        },
        {
            "model": "gpt-image-1",
            "prompt": prompt[:3800],
            "n": 1,
            "size": "1024x1024",
            "quality": "high",
        },
        {
            "model": "dall-e-3",
            "prompt": prompt[:3800],
            "n": 1,
            "size": size if size in {"1024x1024", "1024x1792", "1792x1024"} else "1024x1024",
            "quality": "hd",
        },
    ]
    last_err = None
    for payload in payloads:
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
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            row = (data.get("data") or [{}])[0]
            b64 = row.get("b64_json")
            if b64:
                return base64.b64decode(b64)
            url = row.get("url")
            if url:
                with urllib.request.urlopen(url, timeout=60) as img_resp:
                    return img_resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:400]
            last_err = f"HTTP {exc.code}: {body}"
            if exc.code in {400, 404}:
                continue
            logger.warning("OpenAI Images %s", last_err)
            return None
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            logger.warning("OpenAI Images failed: %s", exc)
            return None
    if last_err:
        logger.warning("OpenAI Images failed after retries: %s", last_err)
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


def build_slide_prompt(
    title: str,
    body: str,
    *,
    theme_hint: str = "",
    article_title: str = "",
    article_summary: str = "",
    article_category: str = "",
    article_source: str = "",
    key_facts: str = "",
) -> str:
    news_bits = [
        article_title.strip(),
        article_summary.strip()[:420],
        f"Category: {article_category}" if article_category else "",
        f"Source: {article_source}" if article_source else "",
        key_facts.strip()[:280],
    ]
    news_context = " | ".join(b for b in news_bits if b)
    topic = f"{title}. {body}".strip()[:420]
    theme = (theme_hint or article_category or article_title or "current affairs technology law").strip()[:180]
    return (
        "Premium editorial social-media hero image, magazine cover quality. "
        "Cinematic lighting, rich color grade (deep navy, teal, warm amber accents), "
        "photoreal or high-end 3D, shallow depth of field. "
        "Concrete metaphors from the news (courts, data centers, borders, cybersecurity, contracts) — "
        "avoid generic glowing AI chips and stock smiling people. "
        "NO text, NO logos, NO watermarks, NO UI, NO captions. "
        f"News context: {news_context or topic}. "
        f"Theme: {theme}. "
        f"Concept: {topic}"
    )


def build_social_hero_prompt(
    *,
    platform: str,
    news_title: str,
    theme: str = "",
    market: str = "",
    hook: str = "",
) -> str:
    """Prompt orientado a creatividades publicables (no plantilla)."""
    subject = (news_title or hook or theme or "inteligencia artificial y regulación").strip()[:220]
    mood = {
        "linkedin": "executive credibility, restrained luxury, wide negative space",
        "instagram": "bold vertical composition, strong single focal subject, scroll-stopping",
        "facebook": "clear wide narrative scene, serious documentary tone",
        "tiktok": "dynamic vertical energy, one strong focal prop filling the frame",
        "youtube": "cinematic widescreen still, high contrast key light",
    }.get(platform, "premium editorial")
    return (
        f"Create a {platform} social post hero image. Style: {mood}. "
        f"Conceptual still-life inspired by: {subject}. "
        f"Theme: {(theme or 'AI governance and law').strip()[:120]}. "
        f"Market cue: {(market or 'Mexico / LatAm / US').strip()[:80]}. "
        "STRICT SUBJECT: objects only — sealed legal folders, fountain pen, "
        "gavel, fiber-optic cables, server rack bokeh, passport stamps, "
        "glass desk, architectural concrete. "
        "Look like a Bloomberg Businessweek still-life cover photo. "
        "Cinematic key light, deep navy charcoal palette, teal rim light, "
        "subtle film grain, razor sharp, premium advertising quality. "
        "FORBIDDEN: any person, face, hand, body, mannequin, robot humanoid, "
        "android, statue, silhouette of a human, portrait. "
        "FORBIDDEN: text, letters, numbers, logos, watermarks, captions, UI. "
        "FORBIDDEN: cartoon, sticker collage, generic neon brain chip."
    )


def _short_hook(text: str, max_len: int = 72) -> str:
    t = " ".join((text or "").split())
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(".,;:") + "…"


def compose_social_hero(
    *,
    ratio: str,
    bg_bytes: bytes | None,
    hook: str,
    brand: str = "Autoridad 360",
) -> bytes:
    """Creatividad social: imagen IA limpia (sin texto encima). Fallback de marca si no hay IA."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps

    width, height = RATIOS.get(ratio, RATIOS["1:1"])

    if bg_bytes:
        try:
            bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
            bg = ImageOps.fit(bg, (width, height), method=Image.Resampling.LANCZOS)
            bg = ImageEnhance.Contrast(bg).enhance(1.06)
            bg = ImageEnhance.Color(bg).enhance(1.04)
            # Marca mínima semitransparente (no copy largo: se veía mal y rompía acentos)
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            brand_font = _load_font(18 if width >= 1000 else 14)
            margin = int(width * 0.045)
            label = brand
            # pill sutil
            tw = int(len(label) * (10 if width >= 1000 else 8))
            od.rounded_rectangle(
                [margin - 6, height - margin - 30, margin + tw + 18, height - margin + 4],
                radius=10,
                fill=(8, 12, 20, 140),
            )
            od.text((margin, height - margin - 24), label, fill=(220, 230, 240, 220), font=brand_font)
            composed = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
            buf = io.BytesIO()
            composed.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except Exception as exc:  # noqa: BLE001
            logger.warning("compose_social_hero AI path failed: %s", exc)

    # Fallback sin IA: tarjeta con jerarquía tipográfica (mejor que el bloque vacío)
    bg = Image.new("RGB", (width, height), (10, 16, 28))
    draw = ImageDraw.Draw(bg)
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=(
                int(10 + 22 * t),
                int(16 + 36 * t),
                int(28 + 50 * t),
            ),
        )
    draw.rectangle([0, 0, int(width * 0.014), height], fill=(56, 189, 248))
    title_font = _load_font(46 if width >= 1000 else 32)
    brand_font = _load_font(20)
    margin = int(width * 0.08)
    y = int(height * 0.28)
    hook_txt = _short_hook(hook, 70)
    for line in textwrap.wrap(hook_txt, width=24)[:4]:
        draw.text((margin, y), line, fill=(248, 250, 252), font=title_font)
        y += 56
    draw.text((margin, height - margin - 36), brand, fill=(148, 163, 184), font=brand_font)
    buf = io.BytesIO()
    bg.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_brand_slide(
    title: str,
    body: str,
    *,
    ratio: str = "4:5",
    bg_bytes: bytes | None = None,
    footer: str = "Autoridad 360",
    slide_label: str | None = None,
) -> bytes:
    """PNG tipográfico de marca para carruseles de pieza; opcionalmente sobre fondo IA."""
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

    width, height = RATIOS.get(ratio, RATIOS["4:5"])
    if bg_bytes:
        try:
            bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
            bg = ImageOps.fit(bg, (width, height), method=Image.Resampling.LANCZOS)
            bg = ImageEnhance.Brightness(bg).enhance(0.72)
            bg = ImageEnhance.Contrast(bg).enhance(1.05)
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

    # Panel semitransparente más liviano (no tapa toda la foto)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    margin = int(width * 0.07)
    panel_top = int(height * 0.42)
    panel_bottom = int(height * 0.92)
    od.rounded_rectangle(
        [margin, panel_top, width - margin, panel_bottom],
        radius=28,
        fill=(15, 23, 42, 168),
    )
    composed = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(composed)

    title_font = _load_font(48 if width >= 1000 else 34)
    body_font = _load_font(30 if width >= 1000 else 22)
    meta_font = _load_font(20)
    footer_font = _load_font(18)

    x = margin + 28
    y = panel_top + 28
    max_chars_title = 30 if width >= 1000 else 22
    max_chars_body = 40 if width >= 1000 else 30

    if slide_label:
        draw.text((x, y), slide_label.upper(), fill=(56, 189, 248), font=meta_font)
        y += 32

    for line in textwrap.wrap((title or "Sin título").strip(), width=max_chars_title)[:3]:
        draw.text((x, y), line, fill=(255, 255, 255), font=title_font)
        y += 54

    y += 10
    for line in textwrap.wrap((body or "").strip(), width=max_chars_body)[:6]:
        draw.text((x, y), line, fill=(226, 232, 240), font=body_font)
        y += 38

    draw.text(
        (x, height - margin - 36),
        footer,
        fill=(148, 163, 184),
        font=footer_font,
    )

    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _article_context_for_piece(db: Session, piece: ContentPiece) -> dict[str, str]:
    """Carga la noticia asociada para anclar el prompt visual."""
    article_id = getattr(piece, "article_id", None)
    if not article_id:
        pkg = getattr(piece, "package", None)
        if pkg is not None:
            article_id = getattr(pkg, "article_id", None)
    if not article_id:
        return {}
    try:
        from app.models.editorial import NewsArticle

        article = db.query(NewsArticle).filter(NewsArticle.id == int(article_id)).first()
    except Exception:  # noqa: BLE001
        return {}
    if not article:
        return {}
    text = (article.summary or article.excerpt or article.full_text or "")[:900]
    facts = []
    for chunk in text.replace("\n", " ").split(". "):
        c = chunk.strip()
        if len(c) > 40:
            facts.append(c[:160])
        if len(facts) >= 3:
            break
    cat = ""
    try:
        cat = article.category.name if article.category else ""
    except Exception:  # noqa: BLE001
        cat = ""
    return {
        "article_title": (article.title or "")[:220],
        "article_summary": (article.summary or article.excerpt or "")[:420],
        "article_category": cat,
        "article_source": (article.source_name or "")[:120],
        "key_facts": " · ".join(facts),
        "article_id": str(article.id),
    }


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
    include_article_context: bool = True,
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
    article_ctx = _article_context_for_piece(db, piece) if include_article_context else {}

    width, height = RATIOS.get(ratio, RATIOS["4:5"])

    for idx, slide in enumerate(slides):
        title = slide.get("title") or f"Slide {idx + 1}"
        body = slide.get("content") or ""
        bg = None
        if use_openai:
            prompt = build_slide_prompt(
                title,
                body,
                theme_hint=article_ctx.get("article_category") or piece.title or "",
                article_title=article_ctx.get("article_title") or "",
                article_summary=article_ctx.get("article_summary") or "",
                article_category=article_ctx.get("article_category") or "",
                article_source=article_ctx.get("article_source") or "",
                key_facts=article_ctx.get("key_facts") or "",
            )
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
        "article_id": article_ctx.get("article_id"),
        "article_title": article_ctx.get("article_title"),
        "include_article_context": bool(article_ctx),
    }
    piece.generation_json = gen
    db.commit()
    db.refresh(piece)

    return {
        "piece_id": piece.id,
        "engine": engine,
        "ratio": ratio,
        "article_context": article_ctx or None,
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


PLATFORM_IMAGE_RATIOS: dict[str, str] = {
    # Dimensiones de salida (Pillow) alineadas a specs de publicación 2025/2026
    "linkedin": "1:1",      # 1080×1080 feed; también válido 1200×627 link (1.91:1)
    "instagram": "4:5",     # 1080×1350 feed (mejor reach que 1:1)
    "facebook": "1.91:1",   # 1200×628 link/feed landscape
    "tiktok": "9:16",       # 1080×1920
    "youtube": "16:9",      # 1920×1080 thumbnail / community
}


def enrich_ad_notes_with_images(
    db: Session,
    notes: dict[str, Any],
    *,
    organization_id: int | None,
    use_openai: bool = True,
    max_openai: int = 2,
) -> dict[str, Any]:
    """Genera creatividad social: prioriza gpt-image-1 + caption mínima (no plantilla fea)."""
    ad_notes = notes.get("ad_notes") if isinstance(notes.get("ad_notes"), list) else []
    if not ad_notes:
        return notes

    org = organization_id if organization_id is not None else 0
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    rel_dir = Path(str(org)) / "hoy-notes" / day
    abs_dir = MEDIA_ROOT / rel_dir
    _ensure_dir(abs_dir)

    openai_used = 0
    openai_failed = False
    brand = "Autoridad 360"
    enriched: list[dict[str, Any]] = []

    for note in ad_notes:
        if not isinstance(note, dict):
            continue
        platform = str(note.get("platform") or "web").lower().strip()
        ratio = PLATFORM_IMAGE_RATIOS.get(platform, "1:1")
        openai_size = "1024x1024"
        if ratio in {"4:5", "9:16"}:
            openai_size = "1024x1792"
        elif ratio in {"1.91:1", "16:9"}:
            openai_size = "1792x1024"

        news_title = str(note.get("news_title") or note.get("theme") or "").strip()
        hook = str(note.get("hook") or news_title or platform.title()).strip()
        news_url = note.get("news_url") or ""
        theme = str(note.get("theme") or "").strip()
        market = str(note.get("market") or "").strip()

        bg = None
        if use_openai and not openai_failed and openai_used < max_openai:
            prompt = build_social_hero_prompt(
                platform=platform,
                news_title=news_title or hook,
                theme=theme,
                market=market,
                hook=hook,
            )
            # Preferir prompt guardado solo si es suficientemente rico
            stored = str(note.get("image_prompt") or "").strip()
            if len(stored) > 80 and ("Premium" in stored or "Create a" in stored or "hero image" in stored):
                prompt = stored
            bg = try_openai_image(db, str(prompt), size=openai_size)
            if bg:
                openai_used += 1
            else:
                openai_failed = True

        try:
            png = compose_social_hero(
                ratio=ratio if ratio in RATIOS else "1:1",
                bg_bytes=bg,
                hook=news_title or hook,
                brand=brand,
            )
            filename = f"{platform}.png"
            abs_path = abs_dir / filename
            abs_path.write_bytes(png)
            # También guardar el raw IA si existe (sin caption) para reuso
            if bg:
                (abs_dir / f"{platform}.raw.png").write_bytes(bg)
            storage_url = f"/media/{rel_dir.as_posix()}/{filename}"
            note = {
                **note,
                "image_url": storage_url,
                "image_ratio": ratio,
                "image_engine": "gpt-image-1" if bg else "pillow-fallback",
                "image_prompt": build_social_hero_prompt(
                    platform=platform,
                    news_title=news_title or hook,
                    theme=theme,
                    market=market,
                    hook=hook,
                ),
            }
            if news_url:
                note["news_url"] = news_url
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo generar imagen para %s: %s", platform, exc)

        enriched.append(note)

    notes = {**notes, "ad_notes": enriched}
    meta = notes.get("meta") if isinstance(notes.get("meta"), dict) else {}
    meta["images_generated"] = sum(1 for n in enriched if n.get("image_url"))
    meta["images_openai"] = openai_used
    notes["meta"] = meta
    return notes
