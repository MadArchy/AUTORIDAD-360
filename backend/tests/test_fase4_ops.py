"""Tests Fase 4 — semáforo y transiciones determinísticas."""

from types import SimpleNamespace

from app.services.risk import (
    assert_transition,
    assess_piece_risk,
    can_approve_with_risk,
    can_transition,
)


def _piece(**kwargs):
    base = {
        "source_url": "https://example.com/a",
        "body_text": "La SEC anunció reglas. Fuente: https://example.com/a",
        "status": "pending_approval",
        "factual_review_json": {"passed": True, "unsupported_claims": []},
        "brand_review_json": {"passed": True, "issues": []},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_green_when_reviews_pass():
    r = assess_piece_risk(_piece())
    assert r.level == "green"
    assert r.can_publish is True


def test_red_when_factual_fails():
    r = assess_piece_risk(
        _piece(
            factual_review_json={"passed": False, "unsupported_claims": ["invento"]},
            status="factual_failed",
        )
    )
    assert r.level == "red"
    assert r.can_publish is False
    ok, code = can_approve_with_risk(r, override=False)
    assert ok is False
    assert "blocked" in code


def test_red_override_requires_reason():
    r = assess_piece_risk(
        _piece(factual_review_json={"passed": False, "unsupported_claims": ["x"]})
    )
    ok_short, _ = can_approve_with_risk(r, override=True, reason="corto")
    assert ok_short is False
    ok, code = can_approve_with_risk(
        r, override=True, reason="Override documentado por revisión legal interna"
    )
    assert ok is True
    assert code == "ok_red_override"


def test_yellow_on_brand_issues():
    r = assess_piece_risk(
        _piece(brand_review_json={"passed": False, "issues": ["hype_banned:gurú"]})
    )
    assert r.level == "yellow"
    ok, _ = can_approve_with_risk(r)
    assert ok is True


def test_slot_transitions():
    assert can_transition("planned", "assigned")
    assert can_transition("approved", "scheduled")
    assert can_transition("scheduled", "published")
    assert not can_transition("published", "planned")
    try:
        assert_transition("published", "approved")
        assert False, "should raise"
    except ValueError:
        pass


def test_task_transitions():
    assert can_transition("todo", "in_progress", kind="task")
    assert can_transition("in_progress", "done", kind="task")
    assert not can_transition("done", "todo", kind="task")


def test_legal_keyword_forces_red():
    r = assess_piece_risk(
        _piece(body_text="Te damos consejo legal vinculante. Fuente: https://example.com/a")
    )
    assert r.level == "red"
    assert any("legal_keyword" in b for b in r.blockers)
