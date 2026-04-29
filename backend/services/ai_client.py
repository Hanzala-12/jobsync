import os
import requests
from dotenv import load_dotenv

load_dotenv()

def ask_llm(prompt: str, system_prompt: str = "You are a helpful career AI assistant.", temperature: float = 0.7) -> str:
    """
    Call LLM API for intelligent analysis.
    Supports both Groq and OpenRouter APIs based on API key format.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return "AI error: API key not configured"
    
    try:
        if api_key.startswith("sk-or-v1-"):
            # OpenRouter API
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/llama-3.1-8b-instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 1024
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                   headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        elif api_key.startswith("gsk_"):
            # Groq API
            from groq import Groq
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1024,
            )
            return completion.choices[0].message.content
        else:
            return "AI error: Invalid API key format"
            
    except Exception as e:
        return f"AI error: {str(e)}"
