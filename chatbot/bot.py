#!/usr/bin/env python3
"""
chatbot/bot.py
Main chatbot entrypoint.

Modes:
  python chatbot/bot.py              — interactive CLI
  python chatbot/bot.py --telegram   — Telegram bot (needs TELEGRAM_BOT_TOKEN)
"""

import os
import argparse
from dotenv import load_dotenv
load_dotenv()

from retriever import Retriever
from prompts import SYSTEM_PROMPT, build_rag_prompt
from llm import call_llm


EMBED_BACKEND = os.environ.get('EMBED_BACKEND', 'nomic')


def get_answer(question, retriever, source_filter=None):
    hits = retriever.search(question, top_k=6, source_filter=source_filter)
    context = retriever.format_context(hits)
    prompt  = build_rag_prompt(question, context)

    answer = call_llm(SYSTEM_PROMPT, prompt)

    # Collect unique source URLs to append
    sources = []
    seen = set()
    for hit in hits:
        url = hit.get('url', '')
        if url and url not in seen and hit['score'] > 0.5:
            seen.add(url)
            label = hit.get('title') or hit.get('source', '')
            sources.append(f"- {label}: {url}")

    if sources:
        answer += '\n\n**Sources:**\n' + '\n'.join(sources[:4])

    return answer, hits


# ── CLI mode ────────────────────────────────────────────────────────────────

def run_cli(retriever):
    model = os.environ.get('LLM_MODEL', 'claude-sonnet-4-6')
    print(f"FOSS United Community Bot (CLI mode) — model: {model}")
    print("Type your question. 'quit' to exit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in ('quit', 'exit'):
            break
        print("\nSearching community knowledge...\n")
        answer, hits = get_answer(question, retriever)
        print(f"Bot: {answer}\n")
        print(f"(Retrieved {len(hits)} context chunks, top score: {hits[0]['score'] if hits else 0})\n")
        print("-" * 60 + "\n")


# ── Telegram bot mode ────────────────────────────────────────────────────────

def run_telegram(retriever):
    try:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError:
        raise ImportError("pip install python-telegram-bot")

    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("Set TELEGRAM_BOT_TOKEN environment variable")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Namaste! I'm the FOSS United community bot.\n\n"
            "Ask me anything about FOSS United — events, chapters, grants, how to contribute, and more.\n\n"
            "I learn from past community discussions on Telegram and the forum."
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        question = update.message.text
        if not question:
            return

        await update.message.reply_text("Searching community knowledge...")

        try:
            answer, hits = get_answer(question, retriever)
            # Telegram doesn't support markdown the same way; clean it up
            answer = answer.replace('**', '*')
            await update.message.reply_text(answer, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(
                f"Sorry, I ran into an error: {e}\n\nTry asking in the forum: https://forum.fossunited.org"
            )

    async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Try asking a question in plain text!")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot running...")
    app.run_polling()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='FOSS United Community Chatbot')
    parser.add_argument('--telegram', action='store_true', help='Run as Telegram bot')
    parser.add_argument('--backend', choices=['nomic', 'openai'], default=EMBED_BACKEND)
    args = parser.parse_args()

    print(f"Loading retriever (backend: {args.backend})...")
    retriever = Retriever(backend=args.backend)
    retriever._load()  # warm up the connection
    print(f"Vector DB ready. {retriever._collection.count()} chunks indexed.")

    if args.telegram:
        run_telegram(retriever)
    else:
        run_cli(retriever)


if __name__ == '__main__':
    main()
