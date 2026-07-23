"""Tests unitarios de lógica determinística (sin DB ni Ollama)."""

from app.services.llm import apply_deterministic_grounding, grounding_score
from app.services.quota import QUOTA_BOOST_FACTOR, PillarQuotaStatus, QuotaSnapshot, pillar_boost_map
from app.services.scoring import WEIGHTS


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_grounding_score_supported():
    source = "La SEC anunció nuevas reglas de disclosure para empresas de inteligencia artificial en 2026."
    claim = "La SEC anunció nuevas reglas de disclosure para IA"
    assert grounding_score(claim, source) >= 0.35


def test_grounding_rejects_hallucination():
    source = "La SEC anunció nuevas reglas de disclosure."
    claim = "El Congreso de México aprobó una reforma fiscal total"
    assert grounding_score(claim, source) < 0.35


def test_deterministic_gate_overrides_model():
    data = {
        "summary_verified": True,
        "unsupported_claims": [],
        "publishable": True,
        "summary": "México legalizó el bitcoin como moneda única",
        "facts": [{"claim": "México legalizó el bitcoin como moneda única", "supported": True}],
    }
    source = "La CNBV emitió una guía sobre activos virtuales sin cambiar el estatus del peso."
    result = apply_deterministic_grounding(data, source)
    assert result["publishable"] is False
    assert len(result["unsupported_claims"]) > 0


def test_quota_boost_for_deficit():
    snapshot = QuotaSnapshot(
        profile_id=1,
        profile_slug="juan-vasquez",
        month_total=10,
        pillars=[
            PillarQuotaStatus(
                pillar_id=1,
                pillar_slug="legal-tech-ia",
                pillar_name="Legal Tech",
                target_pct=20.0,
                actual_pct=0.0,
                deficit_pct=20.0,
                count=0,
            ),
            PillarQuotaStatus(
                pillar_id=2,
                pillar_slug="emprendimiento",
                pillar_name="Emprendimiento",
                target_pct=10.0,
                actual_pct=10.0,
                deficit_pct=0.0,
                count=1,
            ),
        ],
        markets=[],
    )
    boosts = pillar_boost_map(snapshot)
    assert boosts["legal-tech-ia"] == round(1.0 + 0.20 * QUOTA_BOOST_FACTOR, 4)
    assert boosts["emprendimiento"] == 1.0
