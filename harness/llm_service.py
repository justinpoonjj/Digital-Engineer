import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)

def call_llm(prompt: str) -> str: 
    model = os.getenv("LLM_MODEL")

    if not model: 
        raise ValueError("LLM_MODEL is missing from .env")
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content":(
                "You are an AI software engineer working inside a harnessed project. "
                "Folow instructions carefully. Do not claim completion wihtout validation. "
                ),
            },
            {
                "role": "user",
                "content":prompt,
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content or ""