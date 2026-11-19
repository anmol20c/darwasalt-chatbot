"""DarGlobal & Wasalt chatbot server (standard library only).

GET  /        chat UI
GET  /health  status
POST /chat    {"message": str, "history": [...]} -> {"answer", "model", "sources"}
Every response from /chat is JSON, including errors.
"""
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).parent
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODELS = [m.strip() for m in os.getenv(
    "OPENROUTER_MODELS",
    "openrouter/free,meta-llama/llama-3.3-70b-instruct:free,google/gemma-3-27b-it:free",
).split(",") if m.strip()]

INTRO = ("I can answer questions about DarGlobal (Dar Global), the luxury real estate developer, "
         "and Wasalt, the Saudi real estate platform. Try: 'What is Trump Tower Jeddah?', "
         "'What services does Wasalt offer?' or 'How are DarGlobal and Wasalt related?'")

SYSTEM = ("You are an assistant for questions about DarGlobal (Dar Global) and Wasalt. "
          "Answer ONLY from the provided context. If the context does not contain the answer, "
          "say you don't have that information. Be concise and name the company you mean. "
          "Do not invent figures.")


def tokenize(s):
    return re.findall(r"[a-z0-9$]+", s.lower())


def load_docs():
    docs = []
    for name in ("knowledge.json", "scraped.json"):
        p = BASE / "data" / name
        if p.exists():
            docs.extend(json.loads(p.read_text(encoding="utf-8")))
    return docs


DOCS = load_docs()
TOKENS = [tokenize(d["text"] + " " + d["company"]) for d in DOCS]
DF = Counter(t for toks in TOKENS for t in set(toks))
AVGLEN = sum(len(t) for t in TOKENS) / max(len(TOKENS), 1)


def retrieve(query, k=4):
    q = tokenize(query)
    scored = []
    for doc, toks in zip(DOCS, TOKENS):
        tf = Counter(toks)
        score = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (len(DOCS) - DF[t] + 0.5) / (DF[t] + 0.5))
                score += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(toks) / AVGLEN))
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for s, d in scored[:k] if s > 0]


def call_models(messages):
    last = "no API key set"
    if not API_KEY:
        return None, None, last
    for model in MODELS:
        body = json.dumps({"model": model, "messages": messages, "temperature": 0.2}).encode()
        req = urllib.request.Request(OPENROUTER_URL, data=body, headers={
            "Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.load(r)
            text = data["choices"][0]["message"]["content"]
            if text and text.strip():
                return text.strip(), model, ""
            last = f"{model}: empty reply"
        except urllib.error.HTTPError as e:
            last = f"{model}: HTTP {e.code}"
        except Exception as e:
            last = f"{model}: {e}"
    return None, None, last


def answer(message, history):
    ctx = retrieve(message)
    if not ctx:
        return {"answer": INTRO, "model": "none", "sources": []}
    sources = sorted({d["source"] for d in ctx})
    context = "\n\n".join(f"[{d['company']}] {d['text']}" for d in ctx)
    messages = [{"role": "system", "content": SYSTEM + "\n\nContext:\n" + context}]
    messages += [m for m in history[-6:] if m.get("role") in ("user", "assistant")
                 and isinstance(m.get("content"), str)]
    messages.append({"role": "user", "content": message})
    text, model, err = call_models(messages)
    if text:
        return {"answer": text, "model": model, "sources": sources}
    # Model unavailable: still answer from the scraped data instead of failing.
    fallback = "\n\n".join(d["text"] for d in ctx[:2])
    return {"answer": fallback, "model": "retrieval-only (" + err + ")", "sources": sources}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, (BASE / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/health":
            self._send(200, {"status": "ok", "documents": len(DOCS), "models": MODELS,
                             "api_key_set": bool(API_KEY)})
        else:
            self._send(404, {"detail": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/chat":
            return self._send(404, {"detail": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            message = str(req.get("message", "")).strip()
            if not message:
                return self._send(400, {"detail": "message is required"})
            history = req.get("history") or []
            self._send(200, answer(message, history if isinstance(history, list) else []))
        except Exception as e:  # never return HTML
            self._send(500, {"detail": f"server error: {e}"})

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    print(f"Serving {len(DOCS)} chunks on port {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
