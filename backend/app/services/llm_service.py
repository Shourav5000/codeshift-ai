from __future__ import annotations

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-5.6-terra",
        temperature=0,
        timeout=90,
        max_retries=1,
    )