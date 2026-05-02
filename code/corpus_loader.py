"""
corpus_loader.py — Load and chunk support articles from data/.

Supports .json, .md, .txt, and .html files.
Each document chunk carries: text, company, source, chunk_idx.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict

from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_WORDS


# ── Public API ───────────────────────────────────────────────────────────────

def load_corpus() -> List[Dict]:
    """
    Walk data/{hackerrank,claude,visa}/ and return a list of chunk dicts.
    Each chunk: {text, company, source, chunk_idx}
    """
    documents: List[Dict] = []

    company_dirs = {
        "hackerrank": "HackerRank",
        "claude":     "Claude",
        "visa":       "Visa",
    }

    for folder, company_name in company_dirs.items():
        dir_path = Path(DATA_DIR) / folder
        if not dir_path.exists():
            print(f"  [warn] corpus folder not found: {dir_path}")
            continue

        files = list(dir_path.rglob("*"))
        readable = [f for f in files if f.is_file()]
        print(f"  {company_name}: {len(readable)} files")

        for file_path in readable:
            content = _read_file(file_path)
            if not content or len(content.split()) < MIN_CHUNK_WORDS:
                continue

            chunks = _chunk_text(content)
            rel_source = str(file_path.relative_to(DATA_DIR))

            for idx, chunk_text in enumerate(chunks):
                documents.append({
                    "text":      chunk_text,
                    "company":   company_name,
                    "source":    rel_source,
                    "chunk_idx": idx,
                })

    return documents


# ── File reading ─────────────────────────────────────────────────────────────

def _read_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    try:
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                data = json.load(fh)
            return _extract_json_text(data)

        elif ext in {".md", ".txt", ".csv"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read()

        elif ext in {".html", ".htm"}:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                raw = fh.read()
            return _strip_html(raw)

        # skip binaries
    except Exception as exc:
        print(f"  [warn] could not read {file_path}: {exc}")
    return ""


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>",  " ", text,  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── JSON text extraction ──────────────────────────────────────────────────────

_TEXT_KEYS = {"title", "content", "body", "text", "question", "answer",
              "description", "summary", "excerpt", "article", "heading", "name"}

def _extract_json_text(obj, depth: int = 0) -> str:
    if depth > 8:
        return ""
    if isinstance(obj, str):
        return obj.strip()
    if isinstance(obj, dict):
        parts = []
        # Priority: known text fields first
        for key in _TEXT_KEYS:
            if key in obj:
                parts.append(_extract_json_text(obj[key], depth + 1))
        # Then remaining values
        for k, v in obj.items():
            if k not in _TEXT_KEYS:
                parts.append(_extract_json_text(v, depth + 1))
        return " ".join(filter(None, parts))
    if isinstance(obj, list):
        return " ".join(_extract_json_text(item, depth + 1) for item in obj)
    return str(obj)


# ── Chunking ─────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> List[str]:
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    for start in range(0, len(words), step):
        chunk_words = words[start : start + CHUNK_SIZE]
        if len(chunk_words) < MIN_CHUNK_WORDS:
            continue
        chunks.append(" ".join(chunk_words))

    return chunks
