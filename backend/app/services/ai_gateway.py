import time
import json
import logging
import urllib.request
import urllib.error
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import litellm
from litellm import completion
from app.models.ai_providers import AIProvider, AIUsageLog
from app.services.crypto_keys import decrypt_secret_with_rotation, encrypt_secret

logger = logging.getLogger(__name__)

class AIGatewayService:
    def __init__(self, db: Session):
        self.db = db
        self._ensure_default_providers()

    def _ensure_default_providers(self):
        """Seeds default providers if none exist in DB (usa catálogo ai_models)."""
        from app.services.ai_model_catalog import seed_ai_models, resolve_chat_model
        from app.config import settings

        seed_ai_models(self.db)
        count = self.db.query(AIProvider).count()
        if count == 0:
            defaults = [
                AIProvider(
                    name="Ollama Local",
                    provider_type="ollama",
                    model_name=resolve_chat_model(self.db, "ollama", settings.ollama_model),
                    priority=1,
                    is_local=True,
                    is_active=True,
                    base_url=settings.ollama_base_url,
                ),
                AIProvider(
                    name="OpenAI Cloud",
                    provider_type="openai",
                    model_name=resolve_chat_model(self.db, "openai", "gpt-4o"),
                    priority=2,
                    is_local=False,
                    is_active=True,
                    base_url="https://api.openai.com/v1",
                ),
                AIProvider(
                    name="Anthropic Cloud",
                    provider_type="anthropic",
                    model_name=resolve_chat_model(self.db, "anthropic", "claude-3-5-sonnet-20240620"),
                    priority=3,
                    is_local=False,
                    is_active=True,
                    base_url="https://api.anthropic.com/v1",
                ),
            ]
            for p in defaults:
                self.db.add(p)
            self.db.commit()

    def get_active_providers(self) -> List[AIProvider]:
        """Returns active AI providers ordered by priority."""
        return self.db.query(AIProvider).filter(AIProvider.is_active == True).order_by(AIProvider.priority.asc()).all()

    def _log_usage(
        self,
        provider: AIProvider,
        success: bool,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: int,
        error_message: str | None = None,
    ) -> None:
        try:
            log = AIUsageLog(
                provider_id=provider.id,
                task_type="text_generation",
                model_used=provider.model_name,
                is_local=provider.is_local,
                success=success,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                error_message=error_message[:255] if error_message else None,
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def generate_text(self, prompt: str, system_prompt: str = "Eres un asistente experto en IA y Derecho Tech.") -> Dict[str, Any]:
        """
        Executes text generation through the AI Gateway with automatic fallback across providers.
        """
        providers = self.get_active_providers()

        for provider in providers:
            p_start = time.time()
            try:
                if provider.provider_type == "ollama":
                    response_text = self._call_ollama(provider, prompt, system_prompt)
                else:
                    response_text = self._call_cloud_provider(provider, prompt, system_prompt)

                latency_ms = int((time.time() - p_start) * 1000)
                prompt_tokens = max(1, len(prompt) // 4)
                completion_tokens = max(1, len(response_text) // 4)
                total_tokens = prompt_tokens + completion_tokens
                cost_usd = 0.0 if provider.is_local else round((total_tokens / 1000.0) * 0.005, 5)

                # Log successful usage safely
                self._log_usage(
                    provider=provider,
                    success=True,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                )

                return {
                    "provider": provider.provider_type,
                    "model": provider.model_name,
                    "text": response_text,
                    "latency_ms": latency_ms,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": cost_usd,
                    "fallback_triggered": provider.priority > 1
                }

            except Exception as e:
                latency_ms = int((time.time() - p_start) * 1000)
                logger.warning(f"AI Gateway Fallback: Provider {provider.name} failed. Error: {str(e)}")
                
                # Log fallback / error safely
                self._log_usage(
                    provider=provider,
                    success=False,
                    prompt_tokens=len(prompt) // 4,
                    completion_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    error_message=str(e),
                )
                continue

        # Emergency fallback engine removed: strict failure if all providers fail
        raise RuntimeError("All AI providers failed. Check your local Ollama connection or API keys.")


    def _call_ollama(self, provider: AIProvider, prompt: str, system_prompt: str) -> str:
        url = f"{provider.base_url or 'http://localhost:11434'}/api/generate"
        payload = {
            "model": provider.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2, "num_predict": 1200},
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "")

    def _call_cloud_provider(self, provider: AIProvider, prompt: str, system_prompt: str) -> str:
        """Llama a proveedores cloud (OpenAI/Anthropic) utilizando LiteLLM."""
        api_key = None
        if provider.encrypted_api_key:
            api_key, needs_reencrypt = decrypt_secret_with_rotation(provider.encrypted_api_key)
            if needs_reencrypt:
                provider.encrypted_api_key = encrypt_secret(api_key)
                self.db.add(provider)
                self.db.commit()
        else:
            # Fallback a entorno para local dev
            env_key = f"{provider.provider_type.upper()}_API_KEY"
            api_key = os.getenv(env_key)
            
        if not api_key:
            raise ValueError(f"No API Key found for provider {provider.name}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = completion(
            model=provider.model_name,
            messages=messages,
            api_key=api_key,
            temperature=0.2
        )
        return response.choices[0].message.content
