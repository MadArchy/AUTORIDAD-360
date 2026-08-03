"""Persona Juan + agentes de práctica + disclaimers en prompts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.agents.langgraph_runner import list_agents, describe_pipelines
from app.agents.roles import AGENTS, get_agent
from app.agents.tools import TOOL_META
from app.services.juan_persona import (
    DEFAULT_JUAN_PERSONA,
    LEGAL_DISCLAIMER,
    format_persona_system_prompt,
    get_juan_persona_block,
)
from app.services.prompts.content_prompts import GENERATION_PROMPT, LINKEDIN_REWRITE_PROMPT


def test_default_persona_has_voice_and_pillars():
    assert DEFAULT_JUAN_PERSONA["full_name"]
    assert "ai_readiness" in DEFAULT_JUAN_PERSONA["practice_pillars"]
    assert "ip_patents" in DEFAULT_JUAN_PERSONA["practice_pillars"]
    assert DEFAULT_JUAN_PERSONA["disclaimer"] == LEGAL_DISCLAIMER


def test_format_persona_includes_disclaimer_and_name():
    block = format_persona_system_prompt(practice="ai_governance")
    assert "Juan" in block
    assert "no constituye asesoría legal" in block.lower() or LEGAL_DISCLAIMER[:40] in block
    assert "Education" in block or "Governance" in block


def test_get_juan_persona_block_without_db():
    block = get_juan_persona_block(None, practice="ip_patents")
    assert "Patent" in block or "patente" in block.lower() or "IP" in block
    assert "no inventes" in block.lower()


def test_content_prompts_interpolate_persona_block():
    assert "{persona_block}" in GENERATION_PROMPT
    assert "{persona_block}" in LINKEDIN_REWRITE_PROMPT
    filled = GENERATION_PROMPT.format(
        persona_block=get_juan_persona_block(None),
        article_id=1,
        source_url="https://example.com",
        format_type="linkedin",
        language="es",
        language_instruction="español",
        narrative_angle="riesgo",
        summary="resumen",
        key_facts="[]",
        full_text="texto",
    )
    assert "Juan" in filled
    assert LEGAL_DISCLAIMER.split(",")[0] in filled or "asesoría legal" in filled.lower()


def test_juan_agents_registered_with_tools():
    names = {a["name"] for a in list_agents()}
    assert {"juan_editorial", "juan_ai_governance", "juan_ip_patents"} <= names
    assert "draft_juan_editorial" in TOOL_META
    assert "draft_ai_governance_brief" in TOOL_META
    assert "draft_ip_patent_brief" in TOOL_META
    for name in ("juan_editorial", "juan_ai_governance", "juan_ip_patents"):
        agent = get_agent(name)
        assert agent.tools
        assert AGENTS[name] is agent


def test_juan_practice_pipeline_described():
    pipes = describe_pipelines()
    assert "juan_practice" in pipes["modes"]
    assert pipes["steps"]["juan_practice"] == [
        "juan_editorial",
        "juan_ai_governance",
        "juan_ip_patents",
    ]


@patch("app.services.fase5_ai.complete", return_value=("# Brief\n\n" + LEGAL_DISCLAIMER, {"model_used": "mock"}))
def test_ai_governance_brief_contains_disclaimer(mock_complete):
    from app.agents.tools import tool_draft_ai_governance_brief

    db = MagicMock()
    db.info = {}
    result = tool_draft_ai_governance_brief(db, topic="AI governance for boards")
    assert result["practice"] == "ai_governance"
    assert LEGAL_DISCLAIMER in (result.get("brief_markdown") or "")
    assert result["disclaimer"] == LEGAL_DISCLAIMER
    mock_complete.assert_called_once()
    prompt = mock_complete.call_args.kwargs["prompt"]
    assert "Juan" in prompt
    assert LEGAL_DISCLAIMER in prompt


def test_copilot_preamble_uses_juan_voice():
    from app.services.ai_copilot_service import _juan_copilot_preamble

    text = _juan_copilot_preamble(None)
    assert "Juan" in text
    assert "asesoría legal" in text.lower() or LEGAL_DISCLAIMER[:30] in text
