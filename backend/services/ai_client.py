import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(prompt: str, system_prompt: str = "You are a helpful career AI assistant.", temperature: float = 0.7) -> str:
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",   # free tier supported model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI error: {str(e)}"
