#!/usr/bin/env python3
"""
scripts/02_clean_forum.py
Cleans raw Discourse forum posts and groups them into topic-level chunks
for the chatbot knowledge base.

Input:  data/forum_posts.jsonl, data/forum_topics.json
Output: data/chunks_forum.jsonl
"""

import json
import re
from pathlib import Path

POSTS_INPUT  = Path('data/forum_posts.jsonl')
TOPICS_INPUT = Path('data/forum_topics.json')
OUTPUT       = Path('data/chunks_forum.jsonl')

MIN_TEXT_LEN = 20

# Map category_id to human name (from forum API)
CATEGORY_NAMES = {
    1:  'General',
    2:  'Site Feedback',
    6:  'Conference',
    9:  'Interview Series',
    10: 'Meetup',
    12: 'Discussion',
    13: 'News',
    14: 'Project Showcase',
    16: 'Tech for Social Development',
    17: 'Organisation',
    19: 'IndiaFOSS Conference',
    20: 'Hackathon',
    21: 'Mon School',
    25: 'Design',
    27: 'Policy',
    28: 'Community Event',
    29: 'Members',
    32: 'FOSS Help',
    33: 'New Volunteer',
    35: 'Students Program',
    36: 'FOSS United Tech',
    47: 'Industry Partner',
    49: 'Maintainers',
    50: 'Articles We Love',
    53: 'Season of Commits',
}


def clean_text(text):
    if not text:
        return ''
    # Remove quoted blocks (they duplicate content)
    text = re.sub(r'\[quote[^\]]*\].*?\[/quote\]', '', text, flags=re.DOTALL)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove bare links
    text = re.sub(r'(?<!\S)https?://\S+(?!\S)', '[link]', text)
    return text.strip()


def load_posts():
    posts = []
    with open(POSTS_INPUT, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            p['text'] = clean_text(p.get('text', ''))
            posts.append(p)
    return posts


def load_topics():
    with open(TOPICS_INPUT, encoding='utf-8') as f:
        topics = json.load(f)
    return {t['id']: t for t in topics}


def group_by_topic(posts):
    grouped = {}
    for post in posts:
        tid = post['topic_id']
        if tid not in grouped:
            grouped[tid] = []
        grouped[tid].append(post)
    # Sort each topic's posts by post_number
    for tid in grouped:
        grouped[tid].sort(key=lambda p: p.get('post_number', 0))
    return grouped


def make_topic_chunk(topic_meta, posts, category_name):
    """
    Each topic becomes one chunk containing:
    - Title (acts as the 'question' or topic)
    - First post (usually the full description)
    - Top replies (by like count, up to 5)
    """
    if not posts:
        return None

    first_post = posts[0]
    if len(first_post.get('text', '')) < MIN_TEXT_LEN:
        return None

    # Get top replies (excluding first post)
    replies = sorted(posts[1:], key=lambda p: p.get('like_count', 0), reverse=True)[:5]
    replies.sort(key=lambda p: p.get('post_number', 0))

    # Build chunk text
    lines = [
        f"Topic: {topic_meta['title']}",
        f"Category: {category_name}",
        f"",
        f"{first_post.get('username', 'member')}: {first_post['text']}",
    ]

    if replies:
        lines.append('')
        for r in replies:
            if r.get('text') and len(r['text']) >= MIN_TEXT_LEN:
                lines.append(f"{r.get('username', 'member')}: {r['text']}")

    chunk_text = '\n'.join(lines)

    return {
        'source': 'forum',
        'type': 'topic',
        'topic_id': topic_meta['id'],
        'title': topic_meta['title'],
        'category_id': topic_meta.get('category_id'),
        'category': category_name,
        'url': topic_meta.get('url', f"https://forum.fossunited.org/t/{topic_meta['slug']}/{topic_meta['id']}"),
        'created_at': topic_meta.get('created_at', ''),
        'posts_count': len(posts),
        'text': chunk_text,
        'chunk_text': f"[Forum: {category_name}]\n{chunk_text}",
        'participants': list({p.get('username', '') for p in posts[:10] if p.get('username')}),
    }


def make_reply_chunks(topic_meta, posts, category_name):
    """
    For long topics (>10 posts), also create individual reply chunks
    so specific answers are findable.
    """
    chunks = []
    if len(posts) <= 10:
        return chunks

    for post in posts[1:]:
        text = post.get('text', '')
        if len(text) < MIN_TEXT_LEN:
            continue
        chunks.append({
            'source': 'forum',
            'type': 'reply',
            'topic_id': topic_meta['id'],
            'title': topic_meta['title'],
            'category_id': topic_meta.get('category_id'),
            'category': category_name,
            'url': f"{topic_meta.get('url', '')}/{post.get('post_number', '')}",
            'created_at': post.get('created_at', ''),
            'username': post.get('username', ''),
            'text': text,
            'chunk_text': f"[Forum reply in '{topic_meta['title']}']\n{post.get('username', 'member')}: {text}",
            'like_count': post.get('like_count', 0),
        })
    return chunks


def main():
    print(f"Loading posts from {POSTS_INPUT}...")
    posts = load_posts()
    print(f"Loaded {len(posts)} posts")

    print(f"Loading topics from {TOPICS_INPUT}...")
    topics = load_topics()
    print(f"Loaded {len(topics)} topics")

    grouped = group_by_topic(posts)
    print(f"Grouped into {len(grouped)} topics")

    all_chunks = []
    for topic_id, topic_posts in grouped.items():
        topic_meta = topics.get(topic_id, {'id': topic_id, 'title': 'Unknown', 'slug': str(topic_id)})
        cat_id = topic_meta.get('category_id')
        cat_name = CATEGORY_NAMES.get(cat_id, f'Category {cat_id}')

        # Main topic chunk
        chunk = make_topic_chunk(topic_meta, topic_posts, cat_name)
        if chunk:
            all_chunks.append(chunk)

        # Individual reply chunks for long topics
        reply_chunks = make_reply_chunks(topic_meta, topic_posts, cat_name)
        all_chunks.extend(reply_chunks)

    print(f"Created {len(all_chunks)} total chunks")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    print(f"Written to {OUTPUT}")

    # Stats
    types = {}
    cats = {}
    for c in all_chunks:
        types[c['type']] = types.get(c['type'], 0) + 1
        cat = c.get('category', 'unknown')
        cats[cat] = cats.get(cat, 0) + 1

    print("\nBy type:")
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")

    print("\nTop categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat}: {count}")


if __name__ == '__main__':
    main()
