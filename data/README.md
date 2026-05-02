# Corpus Data

Place support articles in the subdirectories:

- `hackerrank/` — HackerRank support articles (JSON, MD, TXT, HTML)
- `claude/`     — Claude / Anthropic support articles
- `visa/`       — Visa support articles

The `corpus_loader.py` will recursively walk each folder and chunk all readable files.
Supported formats: `.json`, `.md`, `.txt`, `.html`, `.htm`, `.csv`
