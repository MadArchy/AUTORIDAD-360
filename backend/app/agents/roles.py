"""Roles de agentes editoriales."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent, extract_json_object
from app.agents.context import AgentContext
from app.services import fase5_ai


class ScoutAgent(BaseAgent):
    name = "scout"
    role = (
        "Explorador web: busca las 11 tipologías de noticias IA/gobernanza/PI/MX-US "
        "del briefing Juan Vásquez"
    )
    tools = ["scout_web"]
    task_type = "agent_plan"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        kwargs: dict[str, Any] = {
            "max_queries": min(14, max(6, ctx.limit * 2)),
            "max_results_per_query": 4,
            "max_priority": int(ctx.extras.get("max_priority") or 11),
            "max_age_hours": int(ctx.extras.get("max_age_hours") or 36),
        }
        if ctx.query:
            kwargs["queries"] = [ctx.query]
        return [("scout_web", kwargs)]


class ClassifierAgent(BaseAgent):
    name = "classifier"
    role = "Clasificador editorial: puntúa y etiqueta artículos recolectados"
    tools = ["classify_one", "classify_batch"]
    task_type = "classify"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        if ctx.article_id:
            return [("classify_one", {"article_id": ctx.article_id})]
        return [("classify_batch", {"limit": ctx.limit})]


class VerifierAgent(BaseAgent):
    name = "verifier"
    role = "Verificador factual: grounding contra la fuente y publicabilidad"
    tools = ["verify_one", "classify_batch"]
    task_type = "verify"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        if ctx.article_id:
            return [("verify_one", {"article_id": ctx.article_id})]
        # Sin article_id: classify_batch ya verifica en el flujo actual
        return [("classify_batch", {"limit": ctx.limit})]


class WriterAgent(BaseAgent):
    name = "writer"
    role = "Redactor multi-formato: genera piezas LinkedIn, blog, newsletter, etc."
    tools = ["write_package"]
    task_type = "generate_content"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        if not ctx.article_id:
            raise ValueError("writer requiere article_id de un artículo verificado")
        return [
            (
                "write_package",
                {
                    "article_id": ctx.article_id,
                    "languages": ctx.languages,
                    "prefer_llm": ctx.prefer_llm,
                },
            )
        ]


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    role = "Revisor: gates factual + marca; opinión LLM opcional"
    tools = ["review_package"]
    task_type = "brand_rewrite"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        package_id = ctx.artifacts.get("package_id") or ctx.extras.get("package_id")
        if not package_id:
            raise ValueError("reviewer requiere package_id (genera primero con writer)")
        return [("review_package", {"package_id": int(package_id)})]

    def run(self, db: Session, ctx: AgentContext, *, reason: bool = True):
        result = super().run(db, ctx, reason=reason)
        # Segunda opinión LLM (asesora; no sustituye gates deterministas)
        try:
            reviews = ctx.artifacts.get("reviews") or []
            prompt = (
                "Eres revisor de marca de Autoridad 360 (voz Juan Vásquez: soberana, "
                "clara, sin hype). Resume en JSON: "
                '{"ok": true|false, "notes": "..."}.\n'
                f"Revisiones: {reviews[:8]}"
            )
            text, meta = fase5_ai.complete(db, task_type="agent_critique", prompt=prompt)
            critique = extract_json_object(text) or {"raw": (text or "")[:400]}
            ctx.set_artifact("llm_critique", critique)
            ctx.log(
                self.name,
                tool="llm_critique",
                status="ok",
                detail=str(critique.get("notes") or critique)[:400],
                data={"model": meta.get("model_used")},
            )
            result.artifacts = dict(ctx.artifacts)
            result.steps = [
                {
                    "agent": s.agent,
                    "tool": s.tool,
                    "status": s.status,
                    "detail": s.detail,
                    "data": s.data,
                    "at": s.at,
                }
                for s in ctx.steps
                if s.agent == self.name
            ]
        except Exception as exc:  # noqa: BLE001
            ctx.log(
                self.name,
                tool="llm_critique",
                status="skip",
                detail=f"Crítica LLM omitida: {exc}",
            )
        return result


class TrendAdAdvisorAgent(BaseAgent):
    name = "trend_ad_advisor"
    role = (
        "Advisor de tendencias sociales: investiga LinkedIn/YouTube/X/TikTok/Instagram "
        "según temas del perfil y sugiere dónde/cómo insertar CTAs orgánicos"
    )
    tools = ["trend_ad_notes"]
    task_type = "agent_plan"

    def plan(self, ctx: AgentContext) -> list[tuple[str, dict[str, Any]]]:
        kwargs: dict[str, Any] = {
            "slug": ctx.extras.get("slug") or "juan-vasquez",
            "max_queries": min(20, max(4, int(ctx.extras.get("max_queries") or 12))),
        }
        return [("trend_ad_notes", kwargs)]


AGENTS: dict[str, BaseAgent] = {
    "scout": ScoutAgent(),
    "classifier": ClassifierAgent(),
    "verifier": VerifierAgent(),
    "writer": WriterAgent(),
    "reviewer": ReviewerAgent(),
    "trend_ad_advisor": TrendAdAdvisorAgent(),
}


def get_agent(name: str) -> BaseAgent:
    agent = AGENTS.get(name.strip().lower())
    if not agent:
        raise KeyError(f"Agente desconocido: {name}. Disponibles: {list(AGENTS)}")
    return agent
