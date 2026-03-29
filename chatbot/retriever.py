"""
chatbot/retriever.py
Handles vector search against the Chroma DB.
"""

import os
from pathlib import Path

CHROMA_DIR = Path('data/chroma')
TOP_K = 6


class Retriever:
    def __init__(self, backend='nomic'):
        self.backend = backend
        self._collection = None
        self._embed_fn = None

    def _load(self):
        if self._collection:
            return

        try:
            import chromadb
        except ImportError:
            raise ImportError("pip install chromadb")

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = client.get_collection('fossunited')

        if self.backend == 'nomic':
            import ollama
            self._embed_fn = lambda text: ollama.embeddings(
                model='nomic-embed-text', prompt=text
            )['embedding']
        elif self.backend == 'openai':
            from openai import OpenAI
            client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
            self._embed_fn = lambda text: client.embeddings.create(
                model='text-embedding-3-small', input=[text]
            ).data[0].embedding

    def search(self, query, top_k=TOP_K, source_filter=None):
        self._load()

        where = None
        if source_filter in ('telegram', 'forum'):
            where = {'source': source_filter}

        query_embedding = self._embed_fn(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=['documents', 'metadatas', 'distances']
        )

        hits = []
        for doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ):
            hits.append({
                'text':     doc,
                'source':   meta.get('source', ''),
                'type':     meta.get('type', ''),
                'url':      meta.get('url', ''),
                'title':    meta.get('title', ''),
                'category': meta.get('category', ''),
                'score':    round(1 - dist, 3),   # cosine similarity
            })

        return hits

    def format_context(self, hits):
        """Format retrieved hits into a context block for the LLM prompt."""
        parts = []
        for i, hit in enumerate(hits, 1):
            source_label = 'Forum' if hit['source'] == 'forum' else 'Telegram'
            header = f"[{source_label}]"
            if hit['title']:
                header += f" {hit['title']}"
            if hit['url']:
                header += f"\nURL: {hit['url']}"
            parts.append(f"--- {i} ({header}) ---\n{hit['text']}")
        return '\n\n'.join(parts)
