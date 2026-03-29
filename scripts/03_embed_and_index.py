#!/usr/bin/env python3
"""
scripts/03_embed_and_index.py
Embeds all chunks and indexes them in a Chroma vector DB.

Supports two embedding backends:
  - nomic (default): free, local via Ollama — run: ollama pull nomic-embed-text
  - openai: text-embedding-3-small (costs money but no local setup)

Usage:
  python scripts/03_embed_and_index.py
  python scripts/03_embed_and_index.py --backend openai
  python scripts/03_embed_and_index.py --reset   # rebuild from scratch
"""

import json
import argparse
import os
from pathlib import Path

CHUNKS_DIR  = Path('data')
CHROMA_DIR  = Path('data/chroma')
BATCH_SIZE  = 50


def load_all_chunks():
    chunks = []
    for fname in ['chunks_telegram.jsonl', 'chunks_forum.jsonl']:
        path = CHUNKS_DIR / fname
        if not path.exists():
            print(f"Warning: {path} not found, skipping")
            continue
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(json.loads(line))
    print(f"Loaded {len(chunks)} chunks total")
    return chunks


def get_embedder_nomic():
    try:
        import ollama
    except ImportError:
        raise ImportError("Install ollama: pip install ollama\nThen: ollama pull nomic-embed-text")

    def embed(texts):
        results = []
        for text in texts:
            r = ollama.embeddings(model='nomic-embed-text', prompt=text)
            results.append(r['embedding'])
        return results

    return embed


def get_embedder_openai():
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install openai: pip install openai")

    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def embed(texts):
        resp = client.embeddings.create(model='text-embedding-3-small', input=texts)
        return [d.embedding for d in resp.data]

    return embed


def build_index(chunks, embed_fn, reset=False):
    try:
        import chromadb
    except ImportError:
        raise ImportError("Install chromadb: pip install chromadb")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            client.delete_collection('fossunited')
            print("Deleted existing collection")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name='fossunited',
        metadata={'hnsw:space': 'cosine'}
    )

    existing = set(collection.get()['ids']) if collection.count() > 0 else set()
    print(f"Existing indexed chunks: {len(existing)}")

    new_chunks = [c for i, c in enumerate(chunks) if str(i) not in existing]
    print(f"New chunks to index: {len(new_chunks)}")

    for i in range(0, len(new_chunks), BATCH_SIZE):
        batch = new_chunks[i:i + BATCH_SIZE]
        texts = [c['chunk_text'][:2000] for c in batch]  # truncate for embedding
        ids   = [str(chunks.index(c)) for c in batch]

        # Build metadata (Chroma only accepts str/int/float/bool)
        metadatas = []
        for c in batch:
            meta = {
                'source':   c.get('source', ''),
                'type':     c.get('type', ''),
                'url':      c.get('url', ''),
                'title':    c.get('title', c.get('topic_title', ''))[:200],
                'category': c.get('category', ''),
                'username': c.get('username', ''),
                'month':    c.get('month', ''),
            }
            metadatas.append(meta)

        try:
            embeddings = embed_fn(texts)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
            print(f"Indexed {i + len(batch)}/{len(new_chunks)} chunks")
        except Exception as e:
            print(f"Error at batch {i}: {e}")

    print(f"\nDone. Total indexed: {collection.count()}")
    return collection


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=['nomic', 'openai'], default='nomic')
    parser.add_argument('--reset', action='store_true', help='Delete and rebuild the index')
    args = parser.parse_args()

    chunks = load_all_chunks()
    if not chunks:
        print("No chunks found. Run 01_clean_telegram.py and 02_clean_forum.py first.")
        return

    print(f"Using embedding backend: {args.backend}")
    if args.backend == 'nomic':
        embed_fn = get_embedder_nomic()
    else:
        embed_fn = get_embedder_openai()

    build_index(chunks, embed_fn, reset=args.reset)


if __name__ == '__main__':
    main()
