# DarGlobal & Wasalt Chatbot

RAG chatbot answering questions about DarGlobal (Dar Global) and Wasalt.

- `scraper.py` – scrapes public pages into `data/scraped.json`
- `data/knowledge.json` – curated chunks from public sources, each with a source URL
- `app.py` – standard-library Python server: BM25 retrieval over chunks, then an OpenRouter free model answers from that context
- `static/index.html` – chat UI
- `Dockerfile` – container image

## Run locally
```bash
pip install -r requirements.txt   # only needed for scraper.py
python scraper.py            # optional: refresh scraped data
export OPENROUTER_API_KEY=sk-or-...
python app.py
```

## Docker
```bash
docker build -t darwasalt-bot .
docker run -p 7860:7860 -e OPENROUTER_API_KEY=sk-or-... darwasalt-bot
```

## Deploy (free) on Hugging Face Spaces
1. Create a Space, SDK = Docker.
2. Push this folder to the Space repo.
3. Settings > Variables and secrets: add secret `OPENROUTER_API_KEY`.
4. Your URL: `https://<user>-<space>.hf.space`

Render alternative: New Web Service from the GitHub repo, runtime Docker, add the env var.

## Models
Defaults try `openrouter/free`, then `meta-llama/llama-3.3-70b-instruct:free`, then `google/gemma-3-27b-it:free`.
Free slugs change; override with `OPENROUTER_MODELS=slug1,slug2`.
