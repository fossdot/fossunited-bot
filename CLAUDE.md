# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

A virtual environment is created at `.venv/` (not committed). Activate it before running anything:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

All scripts must be run from the **repo root** — they use relative paths like `data/...`.

## Pipeline (run in order)

```bash
python scripts/01_clean_telegram.py      # → data/chunks_telegram.jsonl
python scripts/02_clean_forum.py         # → data/chunks_forum.jsonl
python scripts/04_fetch_website.py       # → data/chunks_website.jsonl  (live scrape)
python scripts/03_embed_and_index.py     # → data/chroma/  (takes several minutes)
```

`03_embed_and_index.py` is idempotent — it skips already-indexed chunks. Use `--reset` to rebuild from scratch. Pass `--backend openai` to use OpenAI embeddings instead of the default local Nomic model.

## Running the Chatbot

```bash
# Interactive CLI
python chatbot/bot.py

# Telegram bot (requires TELEGRAM_BOT_TOKEN)
python chatbot/bot.py --telegram

# Web interface at http://localhost:5000
python chatbot/web.py
```

Port for the web interface can be overridden with the `PORT` env var.

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `LLM_MODEL` | No | LiteLLM model string, default `ollama/llama3.1` |
| `ANTHROPIC_API_KEY` | If using Claude models | |
| `OPENAI_API_KEY` | If using GPT models or `--backend openai` | |
| `GROQ_API_KEY` | If using Groq models | |
| `GEMINI_API_KEY` | If using Gemini models | |
| `TELEGRAM_BOT_TOKEN` | Telegram mode only | |
| `EMBED_BACKEND` | No | `nomic` (default) or `openai` |
| `PORT` | No | Web server port, default 5000 |

Set these in a `.env` file at the repo root. `python-dotenv` is loaded in `bot.py` and `web.py`.

## Architecture

Raw data (`data/telegram_messages.jsonl`, `data/forum_posts.jsonl`) is cleaned and chunked by the two cleaning scripts. Telegram messages are grouped into reply threads (up to 10 messages); forum posts are grouped per topic (first post + top replies by likes), with individual reply chunks added for topics with >10 posts. The resulting chunks are embedded and stored in a Chroma vector DB (`data/chroma/`, collection name `fossunited`, cosine similarity space).

At query time, `chatbot/retriever.py` embeds the query with the same backend, searches Chroma for the top 6 hits (optionally filtered by `source: telegram|forum`), and formats them into a context block. `chatbot/prompts.py` wraps this into a RAG prompt which is passed to `chatbot/llm.py`. Sources are included in the response if their cosine similarity score exceeds 0.5 (CLI/Telegram) or 0.45 (web).

`chatbot/llm.py` uses [LiteLLM](https://docs.litellm.ai/docs/providers) — the model is selected via the `LLM_MODEL` env var (default `ollama/llama3.1`). Any LiteLLM-supported model string works. The Chroma collection name (`fossunited`) is hardcoded in `retriever.py`.
