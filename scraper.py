"""Scrape public pages from DarGlobal and Wasalt into data/scraped.json.

Usage: python scraper.py
The app merges data/scraped.json with data/knowledge.json at startup.
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PAGES = [
    ("DarGlobal", "https://darglobal.co.uk/"),
    ("DarGlobal", "https://darglobal.co.uk/about-us"),
    ("DarGlobal", "https://darglobal.co.uk/press/darglobal-breaks-ground-on-trump-tower-jeddah"),
    ("Wasalt", "https://wasalt.com/en/about"),
    ("Wasalt", "https://wasalt.sa/en"),
    ("Wasalt", "https://wasalt.sa/en/corporate"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; assignment-bot/1.0)"}
OUT = Path(__file__).parent / "data" / "scraped.json"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk(text: str, size: int = 700):
    words, buf = text.split(), []
    for w in words:
        buf.append(w)
        if sum(len(x) + 1 for x in buf) >= size:
            yield " ".join(buf)
            buf = []
    if buf:
        yield " ".join(buf)


def scrape():
    records = []
    for company, url in PAGES:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as exc:  # keep going if a page is blocked
            print(f"skip {url}: {exc}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        text = clean(soup.get_text(" "))
        for i, part in enumerate(chunk(text)):
            if len(part) > 120:
                records.append({"id": f"{company[:2].lower()}-s-{len(records)}",
                                "company": company, "source": url, "text": part})
        print(f"ok   {url}")
        time.sleep(1)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=1))
    print(f"wrote {len(records)} chunks to {OUT}")


if __name__ == "__main__":
    scrape()
