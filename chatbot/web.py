#!/usr/bin/env python3
"""
chatbot/web.py
Web interface for the chatbot.

Usage:
  python chatbot/web.py
  Open http://localhost:5000
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template_string
from retriever import Retriever
from prompts import SYSTEM_PROMPT, build_rag_prompt
from llm import call_llm

app = Flask(__name__)
retriever = None

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FOSS United Community Bot</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #f7f7f5;
    --surface: #ffffff;
    --border: #e5e5e2;
    --text: #1a1a1a;
    --text-muted: #6b6b6b;
    --accent: #1a1a1a;
    --accent-fg: #ffffff;
    --user-bg: #1a1a1a;
    --user-fg: #ffffff;
    --bot-bg: #ffffff;
    --radius: 14px;
    --font: system-ui, -apple-system, sans-serif;
    --font-mono: ui-monospace, 'Cascadia Code', monospace;
  }

  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Header ── */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }
  .logo {
    width: 32px; height: 32px;
    background: var(--accent);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: var(--accent-fg);
    font-size: 1rem;
    flex-shrink: 0;
  }
  header h1 { font-size: 0.95rem; font-weight: 600; line-height: 1.2; }
  header p  { font-size: 0.78rem; color: var(--text-muted); }

  /* ── Filter pills ── */
  .filter-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 0.5rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-shrink: 0;
  }
  .filter-label { font-size: 0.78rem; color: var(--text-muted); margin-right: 0.25rem; }
  .pill {
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: transparent;
    font-size: 0.78rem;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.15s;
    font-family: var(--font);
  }
  .pill:hover { border-color: var(--accent); color: var(--accent); }
  .pill.active { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }

  /* ── Messages ── */
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 0;
    scroll-behavior: smooth;
  }
  .msg-row {
    display: flex;
    padding: 0.25rem 1.25rem;
    max-width: 780px;
    margin: 0 auto;
    width: 100%;
  }
  .msg-row.user { justify-content: flex-end; }
  .msg-row.bot  { justify-content: flex-start; }

  .bubble {
    padding: 0.75rem 1rem;
    border-radius: var(--radius);
    max-width: min(88%, 560px);
    font-size: 0.9rem;
    line-height: 1.65;
  }
  .msg-row.user .bubble {
    background: var(--user-bg);
    color: var(--user-fg);
    border-bottom-right-radius: 4px;
  }
  .msg-row.bot .bubble {
    background: var(--bot-bg);
    border: 1px solid var(--border);
    border-bottom-left-radius: 4px;
  }

  /* ── Markdown inside bot bubbles ── */
  .bubble h1, .bubble h2, .bubble h3 {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0.9em 0 0.3em;
  }
  .bubble h1:first-child,
  .bubble h2:first-child,
  .bubble h3:first-child { margin-top: 0; }
  .bubble p { margin: 0.45em 0; }
  .bubble p:first-child { margin-top: 0; }
  .bubble p:last-child  { margin-bottom: 0; }
  .bubble ul, .bubble ol {
    padding-left: 1.3em;
    margin: 0.4em 0;
  }
  .bubble li { margin: 0.2em 0; }
  .bubble strong { font-weight: 600; }
  .bubble em { font-style: italic; }
  .bubble a {
    color: #2563eb;
    text-decoration: underline;
    text-underline-offset: 2px;
    word-break: break-word;
  }
  .bubble a:hover { color: #1d4ed8; }
  .bubble code {
    font-family: var(--font-mono);
    font-size: 0.82em;
    background: #f0f0ed;
    border-radius: 4px;
    padding: 0.1em 0.35em;
  }
  .bubble pre {
    background: #f0f0ed;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    overflow-x: auto;
    margin: 0.6em 0;
    font-size: 0.82em;
    line-height: 1.5;
  }
  .bubble pre code {
    background: none;
    padding: 0;
    border-radius: 0;
    font-size: inherit;
  }
  .bubble blockquote {
    border-left: 3px solid var(--border);
    padding-left: 0.75rem;
    color: var(--text-muted);
    margin: 0.5em 0;
  }
  .bubble hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0.75em 0;
  }

  /* Typing indicator */
  .typing-dots {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0.5rem 0.25rem;
    height: 1.65rem;
  }
  .typing-dots span {
    width: 6px; height: 6px;
    background: var(--text-muted);
    border-radius: 50%;
    animation: bounce 1.2s infinite;
    opacity: 0.5;
  }
  .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
  .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
    40%           { transform: translateY(-5px); opacity: 1; }
  }

  /* ── Input area ── */
  #input-area {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 0.75rem 1.25rem 1rem;
    flex-shrink: 0;
  }
  #input-wrap {
    display: flex;
    gap: 0.5rem;
    max-width: 780px;
    margin: 0 auto;
  }
  #q {
    flex: 1;
    padding: 0.65rem 1rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    font-size: 0.9rem;
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    outline: none;
    transition: border-color 0.15s;
  }
  #q:focus { border-color: var(--accent); }
  #q::placeholder { color: var(--text-muted); }
  #send {
    padding: 0.65rem 1.1rem;
    background: var(--accent);
    color: var(--accent-fg);
    border: none;
    border-radius: 10px;
    font-size: 0.9rem;
    font-family: var(--font);
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.35rem;
    transition: opacity 0.15s;
  }
  #send:hover   { opacity: 0.85; }
  #send:disabled { opacity: 0.4; cursor: not-allowed; }
  #send svg { width: 16px; height: 16px; }
</style>
</head>
<body>

<header>
  <div class="logo">F</div>
  <div>
    <h1>FOSS United Community Bot</h1>
    <p>Answers from Telegram &amp; forum discussions · Powered by AI</p>
  </div>
</header>

<div class="filter-bar">
  <span class="filter-label">Search in:</span>
  <button class="pill active" onclick="setFilter(this,'all')">All sources</button>
  <button class="pill" onclick="setFilter(this,'forum')">Forum</button>
  <button class="pill" onclick="setFilter(this,'telegram')">Telegram</button>
</div>

<div id="messages">
  <div class="msg-row bot">
    <div class="bubble">
      <p>Namaste! Ask me anything about FOSS United — events, chapters, grants, contributing, and more. I draw from past Telegram discussions and forum posts.</p>
    </div>
  </div>
</div>

<div id="input-area">
  <div id="input-wrap">
    <input id="q" type="text" placeholder="Ask a question…"
           autocomplete="off" autocorrect="off" spellcheck="false"
           onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}">
    <button id="send" onclick="send()">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 8H2M8 2l6 6-6 6"/>
      </svg>
      Ask
    </button>
  </div>
</div>

<script>
let filter = 'all';
let busy   = false;

marked.setOptions({ breaks: true, gfm: true });

function setFilter(btn, val) {
  filter = val;
  document.querySelectorAll('.pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

function addMsg(role, html, isMarkdown) {
  const row  = document.createElement('div');
  row.className = 'msg-row ' + role;
  const bub = document.createElement('div');
  bub.className = 'bubble';
  if (isMarkdown) {
    bub.innerHTML = DOMPurify.sanitize(marked.parse(html));
  } else {
    bub.innerHTML = html;
  }
  row.appendChild(bub);
  document.getElementById('messages').appendChild(row);
  row.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return row;
}

function addTyping() {
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  row.id = 'typing';
  row.innerHTML = '<div class="bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
  document.getElementById('messages').appendChild(row);
  row.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return row;
}

async function send() {
  if (busy) return;
  const q = document.getElementById('q').value.trim();
  if (!q) return;

  document.getElementById('q').value = '';
  addMsg('user', q, false);

  busy = true;
  document.getElementById('send').disabled = true;

  const typing = addTyping();

  try {
    const resp = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, source: filter })
    });
    typing.remove();

    if (!resp.ok) throw new Error('Server error ' + resp.status);
    const data = await resp.json();
    addMsg('bot', data.answer, true);
  } catch (e) {
    typing.remove();
    addMsg('bot', '<em style="color:#c00">Something went wrong — please try again.</em>', false);
    console.error(e);
  } finally {
    busy = false;
    document.getElementById('send').disabled = false;
    document.getElementById('q').focus();
  }
}
</script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '').strip()
    source   = data.get('source', 'all')
    if not question:
        return jsonify({'error': 'empty question'}), 400

    source_filter = source if source in ('telegram', 'forum') else None
    hits    = retriever.search(question, top_k=6, source_filter=source_filter)
    context = retriever.format_context(hits)
    prompt  = build_rag_prompt(question, context)

    answer = call_llm(SYSTEM_PROMPT, prompt)
    return jsonify({'answer': answer})


def main():
    global retriever, client
    backend = os.environ.get('EMBED_BACKEND', 'nomic')
    print(f'Loading retriever (backend: {backend})...')
    retriever = Retriever(backend=backend)
    retriever._load()
    print(f'Vector DB ready. {retriever._collection.count()} chunks indexed.')

    port = int(os.environ.get('PORT', 5000))
    print(f'Starting web server on http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
