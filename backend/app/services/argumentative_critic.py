import json
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session
from app.services.fase5_ai import complete

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """Eres un editor estricto experto en Derecho Tech e Inteligencia Artificial corporativa.
Tu objetivo es evaluar el BORRADOR de un artículo generado frente a su TEXTO FUENTE original.
Debes verificar la "Profundidad Argumentativa" del borrador (0 a 100).
Criterios para buen puntaje (80-100):
- Tiene una tesis o postura clara.
- Menciona implicaciones reales, regulaciones específicas o riesgos concretos que aparecen en la fuente.
- Es útil y accionable para líderes corporativos o abogados (da un "so what?").

Criterios para mal puntaje (< 80):
- Es un resumen superficial y genérico.
- No cita leyes, riesgos o impactos específicos.
- Carece de perspectiva crítica o análisis.

Devuelve JSON estricto con la siguiente estructura:
{{
  "argumentative_score": <número de 0 a 100>,
  "critique": "<Resumen de qué le falta o qué hace bien en su argumentación>",
  "suggestions": ["Sugerencia 1", "Sugerencia 2"]
}}

TEXTO FUENTE:
\"\"\"
{source_text}
\"\"\"

BORRADOR GENERADO:
\"\"\"
{draft_text}
\"\"\"
"""

class ArgumentativeCriticService:
    def __init__(self, db: Session):
        self.db = db
        self._complete = complete

    def evaluate_argument(self, draft_text: str, source_text: str) -> Dict[str, Any]:
        """
        Evalúa la profundidad argumentativa del borrador generado respecto a la fuente original.
        """
        try:
            # Limitar longitud para no saturar contexto, enfocándonos en el núcleo
            source_excerpt = source_text[:6000] if source_text else ""
            draft_excerpt = draft_text[:3000] if draft_text else ""

            prompt = CRITIC_PROMPT.format(source_text=source_excerpt, draft_text=draft_excerpt)
            raw_text, _meta = self._complete(
                self.db,
                task_type="agent_critique",
                prompt=(
                    "Eres un crítico argumentativo implacable. Devuelve SOLO JSON.\n\n"
                    + prompt
                ),
            )

            # Limpiar posible markdown en la respuesta JSON
            start = raw_text.find('{')
            end = raw_text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = raw_text[start:end]
                data = json.loads(json_str)
                # Validar campos requeridos
                score = data.get("argumentative_score", 0)
                if not isinstance(score, (int, float)):
                    score = 0
                
                return {
                    "argumentative_score": float(score),
                    "critique": str(data.get("critique", "Fallo al procesar la crítica.")),
                    "suggestions": data.get("suggestions", [])
                }
            
            logger.warning(f"Respuesta del LLM no era JSON válido: {raw_text}")
            return {
                "argumentative_score": 75.0,
                "critique": "Crítico omitido: respuesta no JSON. No se fuerza reescritura.",
                "suggestions": [],
                "provider_failed": True,
                "skip_rewrite": True,
            }
            
        except Exception as e:
            logger.error(f"Fallo en evaluación argumentativa IA: {e}")
            # No devolver score 0: eso disparaba rewrites infinitos y timeouts en Ollama
            return {
                "argumentative_score": 75.0,
                "critique": f"Crítico no disponible ({e}). Se conserva el borrador original.",
                "suggestions": [],
                "provider_failed": True,
                "skip_rewrite": True,
            }
