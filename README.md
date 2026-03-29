# FOSS United Community Chatbot

A RAG-based chatbot that learns from the FOSS United Telegram archive and Discourse forum to help new members get instant answers.

## Architecture

```
Data Sources                 Pipeline                    Chatbot
─────────────               ─────────                   ───────
Telegram archive     →      clean + chunk       →       Chroma vector DB
(tg.fossunited.org)         embed (nomic)               ↓
                                                         LLM via LiteLLM (RAG)
Discourse forum      →      clean + chunk       →       ↓
(forum.fossunited.org)      embed (nomic)               Answer + source links
```

## Project Structure

```
fossunited-chatbot/
├── data/
│   ├── telegram_messages.jsonl     # raw Telegram messages
│   ├── forum_posts.jsonl           # raw Discourse posts
│   ├── chunks.jsonl                # processed chunks ready for embedding
│   └── chroma/                     # vector DB (created at runtime)
├── scripts/
│   ├── 01_clean_telegram.py        # clean + chunk Telegram data
│   ├── 02_clean_forum.py           # clean + chunk forum data
│   ├── 03_embed_and_index.py       # embed chunks, build Chroma DB
│   └── 04_export_browser_data.js   # run in browser console to export scraped data
├── chatbot/
│   ├── bot.py                      # main chatbot (CLI + Telegram bot)
│   ├── web.py                      # web interface
│   ├── llm.py                      # LLM-agnostic wrapper (LiteLLM)
│   ├── retriever.py                # vector search logic
│   └── prompts.py                  # system prompt and RAG prompt templates
├── requirements.txt
└── README.md
```

## Setup

```bash
# 1. Clone and install
cd fossunited-chatbot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Export scraped data from browser (see scripts/04_export_browser_data.js)
# Run that script in the browser console on tg.fossunited.org and forum.fossunited.org
# Save outputs to data/telegram_messages.jsonl and data/forum_posts.jsonl

# 3. Clean and chunk
python scripts/01_clean_telegram.py
python scripts/02_clean_forum.py

# 4. Embed and build vector DB
python scripts/03_embed_and_index.py

# 5. Run chatbot
python chatbot/bot.py
```

## Environment Variables

```bash
# LLM selection (default: ollama/llama3.1 — no key needed)
LLM_MODEL=ollama/llama3.1

# Set only if using a hosted provider:
ANTHROPIC_API_KEY=...    # for claude-* models
OPENAI_API_KEY=...       # for gpt-* models
GROQ_API_KEY=...         # for groq/* models
GEMINI_API_KEY=...       # for gemini/* models

# Embedding backend
EMBED_BACKEND=nomic      # default; use "openai" for OpenAI embeddings
OPENAI_API_KEY=...       # required only if EMBED_BACKEND=openai

# Telegram bot
TELEGRAM_BOT_TOKEN=...   # required only for --telegram mode

# Web server
PORT=5000                # default port
```

Set these in a `.env` file at the repo root.

## Models

### LLM (default: `ollama/llama3.1`)

The chatbot uses [LiteLLM](https://docs.litellm.ai/docs/providers) so any supported model works out of the box:

| `LLM_MODEL` value         | Provider          | Key needed          |
|---------------------------|-------------------|---------------------|
| `ollama/llama3.1`         | Local Ollama      | None                |
| `ollama/deepseek-r1:8b`   | Local Ollama      | None                |
| `claude-sonnet-4-6`       | Anthropic         | `ANTHROPIC_API_KEY` |
| `gpt-4o`                  | OpenAI            | `OPENAI_API_KEY`    |
| `groq/llama3-8b-8192`     | Groq              | `GROQ_API_KEY`      |
| `gemini/gemini-pro`       | Google            | `GEMINI_API_KEY`    |

Full list: https://docs.litellm.ai/docs/providers

### Embedding (default: `nomic-embed-text` via Ollama)

Pass `--backend openai` to use OpenAI's `text-embedding-3-small` instead.

### Vector DB

Chroma — open source, runs fully locally.

## Data Sources

- Telegram: ~12,800 messages from tg.fossunited.org (Jul 2020 - Mar 2024)
- Forum: ~947 topics from forum.fossunited.org (all categories)
