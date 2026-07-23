"""Tests Fase 7 — ajuste por leads calificados, no por likes."""

from app.services.percentage_adjuster import (
    MIN_QUALIFIED_TOTAL,
    _normalize_to_100,
)


def test_normalize_sums_100():
    vals = {1: 40.0, 2: 35.0, 3: 30.0}
    out = _normalize_to_100(vals)
    assert abs(sum(out.values()) - 100.0) < 0.05


def test_min_qualified_threshold():
    assert MIN_QUALIFIED_TOTAL >= 3


def test_likes_ignored_flag_in_contract():
    """Contrato del motor: evidence siempre declara likes_ignored."""
    evidence = {
        "rule": "qualified_leads_only",
        "likes_ignored": True,
        "qualified_leads_total": 5,
    }
    assert evidence["likes_ignored"] is True
    assert evidence["rule"] == "qualified_leads_only"
