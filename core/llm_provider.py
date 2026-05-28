"""
LLM Provider Factory - Supports multiple LLM backends with tenacity retries
"""
import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

load_dotenv()

logger = logging.getLogger("jobsync.llm_provider")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


LLM_FALLBACK_MODE = _env_flag("LLM_FALLBACK_MODE", False)


DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
DEFAULT_NOVITA_BASE_URL = os.getenv("NOVITA_BASE_URL", "https://api.novita.ai/openai")
DEFAULT_NOVITA_MODEL = os.getenv("NOVITA_MODEL", "deepseek/deepseek-v4-pro")
DEFAULT_GROQ_MODEL = os.getenv("LLM_MODEL_GROQ", "llama3-8b-8192")


@dataclass(frozen=True)
class _LLMBackend:
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


def is_fallback_mode_enabled() -> bool:
    return LLM_FALLBACK_MODE

try:
    import httpx
    HTTPX_TIMEOUT = httpx.TimeoutException
except ImportError:
    class HTTPX_TIMEOUT(Exception):
        pass


def _should_retry_exception(exception: Exception) -> bool:
    # Check for requests/httpx network exceptions
    if isinstance(exception, (requests.exceptions.RequestException, HTTPX_TIMEOUT)):
        # If it's an HTTPError, check for specific transient status codes
        if isinstance(exception, requests.exceptions.HTTPError) and exception.response is not None:
            return exception.response.status_code in {429, 500, 502, 503, 504}
        return True
    
    # Check for general status_code property (e.g. from Groq/OpenAI/Httpx custom exceptions)
    status_code = getattr(exception, "status_code", None)
    if status_code in {429, 500, 502, 503, 504}:
        return True
        
    return False


def log_retry(retry_state):
    logger.warning(
        f"LLM call failed (attempt {retry_state.attempt_number}). "
        f"Retrying in {retry_state.next_action.sleep}s... "
        f"Error: {retry_state.outcome.exception()}"
    )


class LLMProvider:
    def __init__(self):
        self.fallback_mode = is_fallback_mode_enabled()
        self.backends = self._build_backends()
        self.provider_type = self.backends[0].provider if self.backends else None
        self.api_key = self.backends[0].api_key if self.backends else ""

    def _build_backends(self) -> list[_LLMBackend]:
        provider_hint = (os.getenv("LLM_PROVIDER") or "").strip().lower()
        candidates = []

        def add_backend(provider: str, api_key: str, model: str, base_url: str | None = None) -> None:
            api_key = (api_key or "").strip()
            if api_key:
                candidates.append(_LLMBackend(provider=provider, api_key=api_key, model=model, base_url=base_url))

        novita_available = bool(os.getenv("NOVITA_API_KEY") or os.getenv("NOVITA_API_KEY_2"))
        preferred_order: list[str] = []

        if provider_hint in {"openrouter", "openai", "novita", "groq"}:
            preferred_order.append(provider_hint)

        if novita_available and "novita" not in preferred_order:
            preferred_order.insert(0, "novita")

        for provider_name in ("openrouter", "openai", "groq"):
            if provider_name not in preferred_order:
                preferred_order.append(provider_name)

        for provider_name in preferred_order:
            self._append_provider_candidates(provider_name, add_backend)

        deduped = []
        seen = set()
        for backend in candidates:
            key = (backend.provider, backend.api_key)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(backend)
        return deduped

    def _append_provider_candidates(self, provider: str, add_backend) -> None:
        if provider == "openrouter":
            add_backend(
                "openrouter",
                os.getenv("OPENROUTER_API_KEY") or "",
                os.getenv("LLM_MODEL_OPENROUTER", DEFAULT_OPENROUTER_MODEL),
                os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
            )
            add_backend(
                "openrouter",
                os.getenv("OPENROUTER_API_KEY_2") or "",
                os.getenv("LLM_MODEL_OPENROUTER_2", os.getenv("LLM_MODEL_OPENROUTER", DEFAULT_OPENROUTER_MODEL)),
                os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
            )
            # Backward compatibility: some environments historically placed the
            # OpenRouter key in GROQ_API_KEY.
            legacy_key = os.getenv("GROQ_API_KEY") or ""
            if legacy_key.startswith("sk-or-v1-"):
                add_backend(
                    "openrouter",
                    legacy_key,
                    os.getenv("LLM_MODEL_OPENROUTER", DEFAULT_OPENROUTER_MODEL),
                    os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
                )
        elif provider == "openai":
            add_backend(
                "openai",
                os.getenv("OPENAI_API_KEY") or "",
                os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
                os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
            )
            add_backend(
                "openai",
                os.getenv("OPENAI_API_KEY_2") or "",
                os.getenv("OPENAI_MODEL_2", os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)),
                os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
            )
            # If a legacy key with an OpenAI-style prefix was placed in GROQ_API_KEY,
            # treat it as OpenAI-compatible.
            legacy_key = os.getenv("GROQ_API_KEY") or ""
            if legacy_key and legacy_key.startswith("sk"):
                add_backend(
                    "openai",
                    legacy_key,
                    os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
                    os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
                )
        elif provider == "novita":
            add_backend(
                "novita",
                os.getenv("NOVITA_API_KEY") or "",
                os.getenv("NOVITA_MODEL", DEFAULT_NOVITA_MODEL),
                os.getenv("NOVITA_BASE_URL", DEFAULT_NOVITA_BASE_URL),
            )
            add_backend(
                "novita",
                os.getenv("NOVITA_API_KEY_2") or "",
                os.getenv("NOVITA_MODEL_2", os.getenv("NOVITA_MODEL", DEFAULT_NOVITA_MODEL)),
                os.getenv("NOVITA_BASE_URL", DEFAULT_NOVITA_BASE_URL),
            )
        elif provider == "groq":
            groq_key = os.getenv("GROQ_API_KEY") or ""
            if not groq_key:
                logger.warning("GROQ_API_KEY is not set; groq provider will be skipped or may fail")
            elif len(groq_key) < 20:
                logger.warning("GROQ_API_KEY appears unusually short and may be invalid")

            add_backend(
                "groq",
                groq_key,
                os.getenv("LLM_MODEL_GROQ", DEFAULT_GROQ_MODEL),
            )
            add_backend(
                "groq",
                os.getenv("GROQ_API_KEY_2") or "",
                os.getenv("LLM_MODEL_GROQ_2", os.getenv("LLM_MODEL_GROQ", DEFAULT_GROQ_MODEL)),
            )
    
    def ask(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Unified interface for LLM calls with retry logic"""
        if self.fallback_mode:
            return "AI error: LLM fallback mode enabled"
        if not self.backends:
            return "AI error: No valid API key configured"
        last_error: Exception | None = None
        for backend in self.backends:
            try:
                return self._call_with_retry(system_prompt, user_prompt, temperature, backend)
            except Exception as exc:
                last_error = exc
                logger.warning("LLM provider %s failed; trying next backend", backend.provider)
        if last_error is not None:
            logger.warning("All LLM backends failed; falling back to local resume generation.")
            return ""
        return ""

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_should_retry_exception),
        before_sleep=log_retry,
        reraise=True
    )
    def _call_with_retry(self, system_prompt: str, user_prompt: str, temperature: float, backend: _LLMBackend) -> str:
        if backend.provider == "openrouter":
            return self._call_openrouter(system_prompt, user_prompt, temperature, backend)
        if backend.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, temperature, backend)
        if backend.provider == "novita":
            return self._call_novita(system_prompt, user_prompt, temperature, backend)
        if backend.provider == "groq":
            return self._call_groq(system_prompt, user_prompt, temperature, backend)
        raise ValueError(f"Unknown provider type: {backend.provider}")
    
    def _call_openrouter(self, system_prompt: str, user_prompt: str, temperature: float, backend: _LLMBackend) -> str:
        url = (backend.base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": backend.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 1024,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float, backend: _LLMBackend) -> str:
        url = (backend.base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": backend.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 1024,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_novita(self, system_prompt: str, user_prompt: str, temperature: float, backend: _LLMBackend) -> str:
        url = (backend.base_url or DEFAULT_NOVITA_BASE_URL).rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": backend.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 1024,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _call_groq(self, system_prompt: str, user_prompt: str, temperature: float, backend: _LLMBackend) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {backend.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": backend.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 1024,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
