"""Agente base: rol + herramientas + paso de razonamiento opcional vía LLM."""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.agents.context import AgentContext, AgentRunResult, new_run_id
from app.agents.tools import TOOL_CATALOG, invoke_tool
from app.services import fase5_ai


class BaseAgent(ABC):
    name: str = "base"
    role: str = "Agente genérico"
    tools: list[str] = []
    task_type: str = "agent_plan"

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "tools": [
                {
                    "name": t,
                    "description": TOOL_CATALOG.get(t, {}).get("description", ""),
                }
                for t in self.tools
            ],
            "task_type": self.task_type,
        }

    def think(self, db: Session, ctx: AgentContext) -> str | None:
        """Razonamiento breve opcional (no bloquea si falla)."""
        try:
            prompt = self._think_prompt(ctx)
            text, meta = fase5_ai.complete(db, task_type=self.task_type, prompt=prompt)
            thought = (text or "").strip()[:600]
            ctx.log(
                self.name,
                tool="think",
                status="think",
                detail=thought or "sin texto",
                data={"model": meta.get("model_used"), "latency_ms": meta.get("latency_ms")},
            )
            return thought
        except Exception as exc:  # noqa: BLE001
            ctx.log(
                self.name,
                tool="think",
                status="skip",
                detail=f"Razonamiento omitido: {exc}",
            )
            return None

    def _think_prompt(self, ctx: AgentContext) -> str:
        tool_lines = "\n".join(
            f"- {t}: {TOOL_CATALOG.get(t, {}).get('description', '')}" for t in self.tools
        )
        return (
            f"Eres el agente «{self.name}» ({self.role}) en Autoridad 360.\n"
            f"Objetivo de la corrida: {ctx.goal}\n"
            f"article_id={ctx.article_id} limit={ctx.limit}\n"
            f"Herramientas disponibles:\n{tool_lines}\n\n"
            "Responde en 2-3 frases: qué vas a hacer y por qué. Sin JSON."
        )

    @abstractmethod
    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        """Lista ordenada de (tool_name, kwargs) a ejecutar."""

    def run(self, db: Session, ctx: AgentContext, *, reason: bool = True) -> AgentRunResult:
        started = time.perf_counter()
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        run_id = new_run_id()
        ok = True
        summary_parts: list[str] = []

        if reason:
            self.think(db, ctx)

        try:
            planned = self.plan(ctx)
        except Exception as exc:  # noqa: BLE001
            ctx.log(self.name, status="error", detail=str(exc)[:500])
            finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return AgentRunResult(
                run_id=run_id,
                agent=self.name,
                ok=False,
                summary=f"plan: {exc}",
                steps=[_step_dict(s) for s in ctx.steps if s.agent == self.name],
                artifacts=dict(ctx.artifacts),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        for tool_name, kwargs in planned:
            try:
                data = invoke_tool(tool_name, db, **kwargs)
                soft_fail = _batch_soft_fail(data)
                status = "error" if soft_fail else "ok"
                if soft_fail:
                    ok = False
                ctx.log(
                    self.name,
                    tool=tool_name,
                    status=status,
                    detail=soft_fail or f"{tool_name} OK",
                    data=_safe_preview(data),
                )
                summary_parts.append(f"{tool_name}: {'error' if soft_fail else 'ok'}")
                self._after_tool(ctx, tool_name, data)
                if soft_fail:
                    break
            except Exception as exc:  # noqa: BLE001
                ok = False
                ctx.log(
                    self.name,
                    tool=tool_name,
                    status="error",
                    detail=str(exc)[:500],
                )
                summary_parts.append(f"{tool_name}: error")
                break

        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        duration_ms = int((time.perf_counter() - started) * 1000)
        return AgentRunResult(
            run_id=run_id,
            agent=self.name,
            ok=ok,
            summary="; ".join(summary_parts) or "sin pasos",
            steps=[_step_dict(s) for s in ctx.steps if s.agent == self.name],
            artifacts=dict(ctx.artifacts),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )

    def _after_tool(self, ctx: AgentContext, tool_name: str, data: dict[str, Any]) -> None:
        if tool_name == "write_package" and data.get("package_id"):
            ctx.set_artifact("package_id", data["package_id"])
            ctx.set_artifact("piece_ids", data.get("piece_ids", []))
        if tool_name == "scout_web":
            ctx.set_artifact("scout_stats", data.get("stats"))
        if tool_name in ("classify_one", "verify_one") and data.get("article_id"):
            ctx.set_artifact("article_id", data["article_id"])
            ctx.set_artifact("article_status", data.get("status"))
        if tool_name == "classify_batch":
            ctx.set_artifact("batch", data)
        if tool_name == "review_package":
            ctx.set_artifact("reviews", data.get("reviews"))


def _step_dict(step: Any) -> dict[str, Any]:
    return {
        "agent": step.agent,
        "tool": step.tool,
        "status": step.status,
        "detail": step.detail,
        "data": step.data,
        "at": step.at,
    }


def _safe_preview(data: dict[str, Any], limit: int = 1200) -> dict[str, Any]:
    raw = json.dumps(data, default=str)
    if len(raw) <= limit:
        return data
    return {"preview": raw[:limit] + "…"}


def _batch_soft_fail(data: dict[str, Any]) -> str | None:
    """Detecta lotes que 'corren' pero no producen resultado útil (p.ej. JSON inválido de Gemma)."""
    if not isinstance(data, dict):
        return None
    errors = data.get("errors")
    processed = data.get("processed")
    if isinstance(errors, list) and processed is not None:
        classified = int(data.get("classified") or 0)
        verified = int(data.get("verified") or 0)
        if int(processed) > 0 and classified == 0 and verified == 0 and errors:
            first = errors[0] if errors else {}
            msg = first.get("error") if isinstance(first, dict) else str(first)
            return f"Lote sin éxito: {msg or 'errores en clasificación'}"
        if int(processed) > 0 and errors and verified == 0 and classified > 0:
            # Clasificó pero verify falló en todos
            first = errors[0] if errors else {}
            msg = first.get("error") if isinstance(first, dict) else str(first)
            return f"Clasificado pero verificación falló: {msg or 'JSON inválido'}"
    return None


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
