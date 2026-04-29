"""
LLM Provider Factory - Supports multiple LLM backends
"""
import os
from dotenv import load_dotenv

load_dotenv()

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
        """Unified interface for LLM calls"""
        if not self.provider_type:
            return "AI error: No valid API key configured"
        
        try:
            if self.provider_type == "openrouter":
                return self._call_openrouter(system_prompt, user_prompt, temperature)
            elif self.provider_type == "groq":
                return self._call_groq(system_prompt, user_prompt, temperature)
        except Exception as e:
            return f"AI error: {str(e)}"
    
    def _call_openrouter(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-3.1-8b-instruct",
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
        from groq import Groq
        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
