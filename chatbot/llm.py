"""
chatbot/llm.py
LLM-agnostic wrapper using LiteLLM.

Set LLM_MODEL env var to pick any supported model:
  claude-sonnet-4-6        Anthropic (default) — needs ANTHROPIC_API_KEY
  gpt-4o                   OpenAI              — needs OPENAI_API_KEY
  ollama/llama3            Local Ollama        — no key needed
  gemini/gemini-pro        Google              — needs GEMINI_API_KEY
  groq/llama3-8b-8192      Groq                — needs GROQ_API_KEY
  mistral/mistral-medium   Mistral             — needs MISTRAL_API_KEY

Full provider list: https://docs.litellm.ai/docs/providers
"""

import os
import litellm

DEFAULT_MODEL = 'ollama/llama3.1'

# Suppress litellm's verbose success logging
litellm.success_callback = []


def call_llm(system: str, user: str, max_tokens: int = 1024) -> str:
    model = os.environ.get('LLM_MODEL', DEFAULT_MODEL)
    response = litellm.completion(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
    )
    return response.choices[0].message.content
