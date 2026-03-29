#!/usr/bin/env python3
"""
scripts/01_clean_telegram.py
Cleans raw Telegram messages and groups them into meaningful chunks
for the chatbot knowledge base.

Input:  data/telegram_messages.jsonl
Output: data/chunks_telegram.jsonl
"""

import json
import re
from pathlib import Path
from datetime import datetime

INPUT  = Path('data/telegram_messages.jsonl')
OUTPUT = Path('data/chunks_telegram.jsonl')

# Min length for a message to be worth indexing
MIN_TEXT_LEN = 30

# Window size for grouping reply threads into one chunk
THREAD_WINDOW = 10


def clean_text(text):
    if not text:
        return ''
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove bare URLs with no surrounding context (they add noise)
    text = re.sub(r'(?<!\S)https?://\S+(?!\S)', '[link]', text)
    return text.strip()


def is_useful(msg):
    text = msg.get('text', '')
    if len(text) < MIN_TEXT_LEN:
        return False
    if msg.get('isService'):
        return False
    # Skip pure link shares
    if text.strip() == '[link]':
        return False
    return True


def load_messages():
    messages = []
    with open(INPUT, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            msg['text'] = clean_text(msg.get('text', ''))
            messages.append(msg)
    return messages


def build_id_index(messages):
    return {m['id']: m for m in messages if m.get('id')}


def group_threads(messages, id_index):
    """
    Groups messages into threads based on reply chains.
    Each thread becomes one chunk with context.
    Standalone messages with no replies become single-message chunks.
    """
    chunks = []
    used_ids = set()

    for msg in messages:
        if msg['id'] in used_ids:
            continue
        if not is_useful(msg):
            used_ids.add(msg['id'])
            continue

        reply_to = msg.get('replyTo', '').strip()

        if reply_to and reply_to in id_index:
            # Part of a thread - find root and collect thread
            root_id = reply_to
            thread = []
            visited = set()

            # Walk up to root
            current = msg
            while True:
                rt = current.get('replyTo', '').strip()
                if rt and rt in id_index and rt not in visited:
                    visited.add(rt)
                    current = id_index[rt]
                else:
                    root_id = current['id']
                    break

            # Collect up to THREAD_WINDOW messages from root forward
            root_idx = next((i for i, m in enumerate(messages) if m['id'] == root_id), None)
            if root_idx is not None:
                thread = [messages[i] for i in range(root_idx, min(root_idx + THREAD_WINDOW, len(messages)))
                          if is_useful(messages[i])]
                for m in thread:
                    used_ids.add(m['id'])

                if thread:
                    chunks.append(make_thread_chunk(thread))
        else:
            # Standalone message
            used_ids.add(msg['id'])
            chunks.append(make_single_chunk(msg))

    return chunks


def make_single_chunk(msg):
    return {
        'source': 'telegram',
        'type': 'message',
        'month': msg.get('month', ''),
        'timestamp': msg.get('time', ''),
        'username': msg.get('username', ''),
        'text': msg['text'],
        'chunk_text': f"[Telegram] {msg.get('username', 'member')}: {msg['text']}",
        'url': f"https://tg.fossunited.org/{msg.get('month', '')}.html#{msg.get('id', '')}",
        'msg_id': msg.get('id', ''),
    }


def make_thread_chunk(thread):
    lines = []
    for m in thread:
        lines.append(f"{m.get('username', 'member')}: {m['text']}")
    combined = '\n'.join(lines)
    first = thread[0]
    return {
        'source': 'telegram',
        'type': 'thread',
        'month': first.get('month', ''),
        'timestamp': first.get('time', ''),
        'participants': list({m.get('username', '') for m in thread}),
        'text': combined,
        'chunk_text': f"[Telegram thread]\n{combined}",
        'url': f"https://tg.fossunited.org/{first.get('month', '')}.html#{first.get('id', '')}",
        'msg_id': first.get('id', ''),
    }


def main():
    print(f"Loading {INPUT}...")
    messages = load_messages()
    print(f"Loaded {len(messages)} messages")

    id_index = build_id_index(messages)
    print("Building thread groups...")
    chunks = group_threads(messages, id_index)
    print(f"Created {len(chunks)} chunks")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    print(f"Written to {OUTPUT}")

    # Stats
    types = {}
    for c in chunks:
        types[c['type']] = types.get(c['type'], 0) + 1
    for t, count in types.items():
        print(f"  {t}: {count}")


if __name__ == '__main__':
    main()
