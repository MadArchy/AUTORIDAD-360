"""Filtros editoriales determinísticos para el piloto Juan Vásquez.

Separan señales IA/gobernanza/MX-US del ruido (crimen, deportes, shipping genérico).
"""

from __future__ import annotations

import re

# Penalización fuerte: no son material de tipologías Juan
NOISE_PATTERNS: list[str] = [
    r"asesinad",
    r"homicidio",
    r"desaparecid",
    r"sin vida",
    r"narco",
    r"c[aá]rtel",
    r"balacera",
    r"feminicidio",
    r"secuestro",
    r"f[uú]tbol",
    r"\bmundial\b",
    r"selecci[oó]n nacional",
    r"liga mx",
    r"champions",
    r"nba\b",
    r"mlb\b",
    r"tenista",
    r"goleador",
    r"telenovela",
    r"influencer",
    r"red carpet",
    r"premios oscar",
    r"cumplea[nñ]os",
    r"remata su causa",
    r"reality show",
    r"far[aá]ndula",
    r"chisme",
    r"espect[aá]culos",
    r"fallecid",
    r"terremoto",
    r"\bsismos?\b",
    r"doblete s[ií]smico",
    r"puntaje perfecto",
    r"examen de la unam",
    r"\bmencho\b",
    r"tumba de",
    r"final del mundial",
    r"\bmuere\b",
    r"muerte de",
    r"platica con",
    # Guías genéricas que contaminan Top 10 / LinkedIn
    r"shipping basics",
    r"shipping documentation",
    r"\bincoterms?\b",
    r"global business navigator",
    r"\bacd_test\b",
]

SIGNAL_PATTERNS: list[str] = [
    r"inteligencia artificial",
    r"\bia\b",
    r"\bai\b",
    r"machine learning",
    r"generativa",
    r"gobernanza",
    r"governance",
    r"\bvisa\b",
    r"inmigraci[oó]n",
    r"immigrat",
    r"uscis",
    r"green card",
    r"h-?1b",
    r"tn\b",
    r"t-?mec",
    r"usmca",
    r"arancel",
    r"tariff",
    r"nearshoring",
    r"compliance",
    r"cumplimiento",
    r"lavado de dinero",
    r"\baml\b",
    r"\bofac\b",
    r"sanciones",
    r"sec\b",
    r"ftc\b",
    r"cnbv",
    r"cofece",
    r"propiedad intelectual",
    r"patente",
    r"inventorship",
    r"copyright",
    r"corporativ",
    r"fusiones? y adquisiciones",
    r"\bm&a\b",
    r"gobierno corporativo",
    r"legaltech",
    r"legal tech",
    r"privacidad",
    r"protecci[oó]n de datos",
    r"lfpdppp",
    r"gdpr",
    r"ccpa",
    r"contrato",
    r"litigio",
    r"demanda",
    r"lawsuit",
    r"regulaci[oó]n",
    r"transfronteriz",
    r"cross-?border",
    r"ciberseguridad",
    r"data breach",
]


def _haystack(title: str | None, *extra: str | None) -> str:
    parts = [title or "", *[e or "" for e in extra]]
    return " ".join(parts).lower()


def noise_hits(title: str | None, *extra: str | None) -> list[str]:
    text = _haystack(title, *extra)
    return [p for p in NOISE_PATTERNS if re.search(p, text, re.IGNORECASE)]


def signal_hits(title: str | None, *extra: str | None) -> list[str]:
    text = _haystack(title, *extra)
    return [p for p in SIGNAL_PATTERNS if re.search(p, text, re.IGNORECASE)]


def is_editorial_noise(title: str | None, summary: str | None = None) -> bool:
    """True si el título (o resumen corto) es claramente ruido no profesional."""
    hits = noise_hits(title, summary)
    title_hits = noise_hits(title)
    if title_hits:
        return True
    return len(hits) >= 2


def editorial_score_multiplier(title: str | None, *extra: str | None) -> float:
    """
    Multiplicador determinístico sobre el score base.
    - Ruido (shipping / GBN / farándula): baja fuerte
    - Señal IA/legal/MX-US: sube moderado
    """
    n = len(noise_hits(title, *extra))
    s = len(signal_hits(title, *extra))
    mult = 1.0
    if n:
        mult *= max(0.15, 1.0 - 0.4 * min(n, 3))
    if s:
        mult *= min(1.4, 1.0 + 0.09 * min(s, 4))
    return round(mult, 3)
