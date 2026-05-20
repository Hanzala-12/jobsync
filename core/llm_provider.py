"""
LLM Provider Factory - Supports multiple LLM backends with tenacity retries
"""
import os
import logging
from dotenv import load_dotenv
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

load_dotenv()

logger = logging.getLogger("jobsync.llm_provider")

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
        self.api_key = os.getenv("GROQ_API_KEY")
        self.provider_type = self._detect_provider()
    
    def _detect_provider(self):
        if not self.api_key:
            return None
        if self.api_key.startswith("sk-or-v1-"):
            return "openrouter"
        elif self.api_key.startswith("gsk_"):
            return "groq"
        return None
    
    def ask(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Unified interface for LLM calls with retry logic"""
        if not self.provider_type:
            return "AI error: No valid API key configured"
        
        try:
            return self._call_with_retry(system_prompt, user_prompt, temperature)
        except Exception as e:
            return f"AI error: {str(e)}"

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_should_retry_exception),
        before_sleep=log_retry,
        reraise=True
    )
    def _call_with_retry(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        if self.provider_type == "openrouter":
            return self._call_openrouter(system_prompt, user_prompt, temperature)
        elif self.provider_type == "groq":
            return self._call_groq(system_prompt, user_prompt, temperature)
        raise ValueError(f"Unknown provider type: {self.provider_type}")
    
    def _call_openrouter(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        model = os.getenv("LLM_MODEL_OPENROUTER", "meta-llama/llama-3.1-8b-instruct")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 1024
        }
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                 headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _call_groq(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        model = os.getenv("LLM_MODEL_GROQ", "llama3-8b-8192")
        from groq import Groq
        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
