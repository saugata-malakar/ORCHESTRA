# Support Triage Agent — `code/`

Terminal-based multi-domain support triage agent for the
**HackerRank Orchestrate** hackathon (May 1–2, 2026).

---

## Architecture

```
support_tickets.csv
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  main.py  (CLI entry point)                           │
│                                                       │
│  ┌──────────────────┐    ┌──────────────────────┐     │
│  │  corpus_loader   │ →  │  BM25Retriever       │     │
│  │  Load + chunk    │    │  Offline dense rank  │     │
│  │  data/ articles  │    │  + company boost     │     │
│  └──────────────────┘    └──────────────────────┘     │
│                                   │                   │
│  ┌──────────────────┐             │ top-K chunks      │
│  │  safety.py       │             ▼                   │
│  │  Rule-based      │    ┌──────────────────────┐     │
│  │  pre-screening   │ →  │  SupportTriageAgent  │     │
│  │  (escalation /   │    │  Claude API call     │     │
│  │   OOS / malice)  │    │  Structured JSON out │     │
│  └──────────────────┘    └──────────────────────┘     │
│                                   │                   │
│                                   ▼                   │
│                           output.csv                  │
└───────────────────────────────────────────────────────┘
```

**Key design decisions:**

| Concern | Approach |
|---|---|
| Retrieval | BM25Okapi (offline, no vector DB needed) with company-affinity boosting (×1.4) |
| LLM | Claude (`claude-sonnet-4-20250514`) via Anthropic SDK, `temperature=0` |
| Escalation | Three-layer: rule-based safety pre-screen + OOS detection + malicious detection **+** LLM judgment |
| Determinism | `random.seed(42)`, `temperature=0`, pinned deps |
| Grounding | Corpus chunks injected verbatim into prompt; LLM instructed not to hallucinate |
| Safety | Prompt injection detection (multi-language), destructive request blocking |

---

## File map

```
code/
├── main.py           Entry point (CLI flags: --sample, --dry-run)
├── config.py         All constants & env-var reading
├── corpus_loader.py  Load + chunk data/ (json, md, txt, html)
├── retriever.py      BM25Retriever with company boosting
├── safety.py         Rule-based escalation, OOS & malice detection
├── prompts.py        System prompt + user prompt builder
├── agent.py          SupportTriageAgent (orchestrator)
├── requirements.txt
└── README.md         ← you are here
```

---

## Setup

### 1. Prerequisites

- Python **3.11+**
- An **Anthropic API key** (set as env var)

### 2. Install dependencies

```bash
cd code/
pip install -r requirements.txt
```

### 3. Set your API key

```bash
# Linux / macOS
export ANTHROPIC_API_KEY=sk-ant-...

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=sk-ant-...

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Or copy `.env.example` → `.env` in the repo root and add your key there.

---

## Running the agent

### Full run (all tickets)

```bash
python main.py
```

Reads  `support_tickets/support_tickets.csv`
Writes `support_tickets/output.csv`

### Sample run (development / sanity check)

```bash
python main.py --sample
```

### Dry run (no API calls — test corpus loading + retrieval)

```bash
python main.py --dry-run
```

### Custom paths

```bash
python main.py --input /path/to/in.csv --output /path/to/out.csv
```

---

## Output format

| Column | Values |
|---|---|
| `status` | `replied` \| `escalated` |
| `product_area` | e.g. `screen`, `account_management`, `card_security` |
| `response` | User-facing answer grounded in corpus |
| `justification` | Internal reasoning for routing decision |
| `request_type` | `product_issue` \| `feature_request` \| `bug` \| `invalid` |

---

## Escalation logic

Three independent safety layers:

1. **Safety pre-screen (`safety.py`)** — regex patterns for fraud,
   account compromise, legal threats, identity theft, prompt injection, etc.
   Any match forces `status = "escalated"`.

2. **Out-of-scope detection** — detects unrelated queries (movies, weather, etc.)
   and flags them for the LLM to handle as `invalid`.

3. **Malicious intent detection** — catches requests for destructive code or
   system manipulation. Forces `request_type = "invalid"`.

4. **LLM judgment** — if corpus doesn't support a confident answer,
   Claude sets `status = "escalated"` itself.

---

## Notes

- **No network calls** at inference time beyond the Anthropic API.
- All random sampling is seeded (`RANDOM_SEED = 42`).
- Rate-limit guard: 0.3s between API calls.
