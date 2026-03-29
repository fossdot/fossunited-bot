#!/bin/bash
# quickstart.sh — sets up and runs the FOSS United chatbot from scratch

set -e

echo "=== FOSS United Community Chatbot Setup ==="

# Check Python
python3 --version || { echo "Python 3 required"; exit 1; }

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check for Ollama (nomic embedding)
if command -v ollama &>/dev/null; then
  echo ""
  echo "Ollama found. Pulling nomic-embed-text model..."
  ollama pull nomic-embed-text
else
  echo ""
  echo "WARNING: Ollama not found. Install from https://ollama.ai to use free local embeddings."
  echo "Or set EMBED_BACKEND=openai and provide OPENAI_API_KEY in .env"
fi

# Check data files
echo ""
if [ ! -f data/telegram_messages.jsonl ]; then
  echo "MISSING: data/telegram_messages.jsonl"
  echo "Run scripts/05_scrape_telegram_full.js in browser on tg.fossunited.org"
  echo "Then export and save to data/telegram_messages.jsonl"
fi

if [ ! -f data/forum_posts.jsonl ]; then
  echo "MISSING: data/forum_posts.jsonl"
  echo "Run the forum scraper in browser on forum.fossunited.org"
  echo "Then export and save to data/forum_posts.jsonl"
fi

if [ ! -f data/telegram_messages.jsonl ] || [ ! -f data/forum_posts.jsonl ]; then
  echo ""
  echo "Please add data files and re-run this script."
  exit 1
fi

# Run pipeline
echo ""
echo "Step 1: Cleaning Telegram data..."
python scripts/01_clean_telegram.py

echo ""
echo "Step 2: Cleaning forum data..."
python scripts/02_clean_forum.py

echo ""
echo "Step 3: Embedding and indexing (this takes a few minutes)..."
python scripts/03_embed_and_index.py

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Start the web interface:"
echo "  python chatbot/web.py"
echo ""
echo "Or start the Telegram bot:"
echo "  python chatbot/bot.py --telegram"
echo ""
echo "Or use the CLI:"
echo "  python chatbot/bot.py"
