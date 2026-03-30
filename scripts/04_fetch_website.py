#!/usr/bin/env python3
"""
scripts/04_fetch_website.py
Scrapes fossunited.org for live content: upcoming events (via RSS), IndiaFOSS,
FOSS Hack, city chapters, and general about info.

Output: data/chunks_website.jsonl (re-run to refresh)

Usage:
  python scripts/04_fetch_website.py
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://fossunited.org'
OUTPUT   = Path('data/chunks_website.jsonl')

HEADERS = {
    'User-Agent': 'fossunited-bot/1.0 (community chatbot; github.com/fossdot/fossunited-bot)'
}


# ── helpers ──────────────────────────────────────────────────────────────────

def get_html(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def get_raw(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def abs_url(href):
    if not href:
        return ''
    if href.startswith('http'):
        return href
    # ensure leading slash
    if not href.startswith('/'):
        href = '/' + href
    return f'{BASE_URL}{href}'


def strip_html(html_str):
    return BeautifulSoup(html_str, 'html.parser').get_text(separator=' ', strip=True)


def make_chunk(text, title, url, type_):
    return {
        'chunk_text': text.strip(),
        'source':     'website',
        'type':       type_,
        'url':        url,
        'title':      title,
        'category':   '',
        'username':   '',
        'month':      '',
    }


# ── scrapers ─────────────────────────────────────────────────────────────────

def fetch_events_rss():
    """Parse upcoming events from the RSS feed — no JS needed."""
    chunks = []
    print("Fetching events RSS feed...")

    try:
        raw = get_raw(f'{BASE_URL}/events/timeline/rss.xml')
        root = ET.fromstring(raw)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'dc': 'http://purl.org/dc/elements/1.1/'}
        items = root.findall('.//item')
        print(f"  Found {len(items)} events")

        for item in items:
            title   = (item.findtext('title') or '').strip()
            link    = (item.findtext('link')  or '').strip()
            pub     = (item.findtext('pubDate') or '').strip()
            creator = (item.findtext('dc:creator', namespaces=ns) or '').strip()
            cat     = (item.findtext('category') or '').strip()
            desc_raw = item.findtext('description') or ''
            desc    = strip_html(desc_raw)

            text = f"{title}\nOrganiser: {creator}\nType: {cat}\nDate: {pub}\nURL: {link}\n\n{desc}"
            chunks.append(make_chunk(text, title, link, 'event'))

    except Exception as e:
        print(f"  Error: {e}")

    return chunks


def fetch_static(url, title, type_):
    """Fetch a static page and extract readable main content."""
    print(f"Fetching {url} ...")
    try:
        soup = get_html(url)
        # Remove noise
        for tag in soup.select('nav, footer, header, script, style, .navbar, .footer, noscript'):
            tag.decompose()
        main = soup.select_one('main, .v3-container, article, .main-content') or soup.body
        if not main:
            return []
        lines = [l.strip() for l in main.get_text(separator='\n').splitlines() if l.strip()]
        text = '\n'.join(lines)[:3000]
        if text:
            return [make_chunk(text, title, url, type_)]
    except Exception as e:
        print(f"  Warning: {e}")
    return []


def fetch_chapters():
    """Fetch active city chapter pages and their events."""
    chunks = []
    print("Fetching city chapters...")

    try:
        soup = get_html(f'{BASE_URL}/city-communities')
        links = soup.select('a.city-card')
        print(f"  Found {len(links)} chapter cards")
    except Exception as e:
        print(f"  Error: {e}")
        return chunks

    for link in links:
        city_el   = link.select_one('.city-name')
        status_el = link.select_one('.chapter-status')
        href      = link.get('href', '')

        if not href:
            continue
        if status_el and 'inactive' in status_el.get_text().lower():
            continue

        city        = city_el.get_text(strip=True) if city_el else href.split('/')[-1]
        chapter_url = abs_url(href)

        try:
            detail = get_html(chapter_url)
            events = detail.select('a.event-container, a[href*="/c/"]')

            text = f"FOSS United {city} Chapter\nPage: {chapter_url}\n\n"

            for ev in events[:6]:
                ev_title = ev.select_one('.event-container-title')
                ev_date  = ev.select_one('.event-container-date-location')
                ev_bio   = ev.select_one('.event-container-bio')
                ev_href  = ev.get('href', '')

                if not ev_title:
                    continue
                text += f"Event: {ev_title.get_text(strip=True)}\n"
                if ev_date:
                    text += f"When/Where: {ev_date.get_text(strip=True)}\n"
                if ev_bio:
                    text += f"{ev_bio.get_text(strip=True)}\n"
                if ev_href:
                    text += f"URL: {abs_url(ev_href)}\n"
                text += '\n'

            chunks.append(make_chunk(text, f'FOSS United {city}', chapter_url, 'community'))
            time.sleep(0.3)
        except Exception as e:
            print(f"  Warning: {chapter_url}: {e}")

    return chunks


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    OUTPUT.parent.mkdir(exist_ok=True)
    chunks = []

    chunks += fetch_events_rss()
    chunks += fetch_static(f'{BASE_URL}/indiafoss/2026', 'IndiaFOSS 2026', 'conference')
    chunks += fetch_static(f'{BASE_URL}/fosshack/2026',  'FOSS Hack 2026',  'hackathon')
    chunks += fetch_static(BASE_URL,                     'FOSS United',     'about')
    chunks += fetch_chapters()

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + '\n')

    print(f"\nWritten {len(chunks)} chunks → {OUTPUT}")


if __name__ == '__main__':
    main()
