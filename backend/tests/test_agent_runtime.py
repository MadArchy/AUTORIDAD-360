"""Tablero y prioridad de agentes automáticos."""

from __future__ import annotations

from app.agents.runtime import (
    AGENT_PRIORITY,
    get_agent_board,
    set_agent_status,
    set_cycle_state,
)


def test_priority_covers_all_registered_agents():
    from app.agents.roles import AGENTS

    names = {a["name"] for a in AGENT_PRIORITY}
    assert names == set(AGENTS.keys())
    priorities = [a["priority"] for a in AGENT_PRIORITY]
    assert priorities == sorted(priorities)


def test_board_marks_running_agent():
    org = 999001
    set_agent_status(
        "scout",
        organization_id=org,
        status="running",
        current_step="scout_web",
        current_tool="scout_web",
        summary="buscando",
    )
    set_cycle_state(org, status="running", phase="discover", current_agent="scout")
    board = get_agent_board(org)
    assert board["active_count"] >= 1
    assert "scout" in board["active"]
    scout = next(a for a in board["agents"] if a["name"] == "scout")
    assert scout["status"] == "running"
    assert scout["current_tool"] == "scout_web"
    assert scout["priority"] == 1
    assert board["cycle"]["status"] == "running"
