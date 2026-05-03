<div align="center">

# 🎵 Orchestra — AI Support Triage Engine

### **[🚀 LIVE APP → https://orchestra-1-41x4.onrender.com](https://orchestra-1-41x4.onrender.com)**

[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render)](https://orchestra-1-41x4.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Powered_by-Google_Gemini-4285F4?style=for-the-badge&logo=google)](https://ai.google.dev)

*A production-grade, deterministic AI triage agent that classifies, screens, and resolves support tickets across HackerRank, Claude, and Visa — powered by Google Gemini Free Tier and offline BM25 retrieval.*

**Built for the HackerRank Orchestrate Hackathon 2026**

</div>

---

## 🌟 10 Groundbreaking Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Gemini Deterministic RAG** | Exact 0.0 temperature with offline BM25Okapi retrieval — zero hallucination by design |
| 2 | **Live WebSocket Streaming** | Real-time dashboard via Flask-SocketIO — tickets appear instantly as the LLM finishes |
| 3 | **TF-IDF Deduplication** | scikit-learn vectorizes tickets; auto-resolves >98% similar ones, saving API costs |
| 4 | **3-Layer Prompt Injection Safety** | Intercepts jailbreaks, base64 obfuscation, and malicious instructions before LLM evaluation |
| 5 | **Multi-Language Detection** | langdetect identifies non-English tickets, translates for retrieval, responds in native language |
| 6 | **Self-Critique Validation** | Secondary LLM pass catches and regenerates hallucinated responses automatically |
| 7 | **Confidence Scoring** | Mathematical 0.0-1.0 score based on BM25 retrieval strength and critique results |
| 8 | **Company Inference** | Auto-detects company (HackerRank/Claude/Visa) via keyword analysis when field is blank |
| 9 | **Audit Trails** | output_audit.json logs every safety flag, retrieval path, and reasoning chain per ticket |
| 10 | **GitHub Actions CI** | Automated evaluation pipeline validates agent accuracy on every push |

---

## 🎨 UI/UX Design

- **Aurora Mesh Gradients** — Animated 3D backgrounds with mouse tracking
- **Bento Box Grid** — Enterprise-grade modular component layout
- **Split-Panel Auth Portal** — Dedicated sign-in with email/password + Google OAuth
- **Real-Time Dashboard** — Live progress bars, confidence scores, and audit flag badges

---

## 📊 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Google Gemini 2.0 Flash (Free Tier) |
| Retrieval | BM25Okapi (Offline, No Vector DB) |
| Backend | Flask + Gunicorn |
| Real-Time | Flask-SocketIO (WebSockets) |
| Auth | Google OAuth 2.0 + Email Login |
| NLP | langdetect + scikit-learn TF-IDF |
| Safety | Regex Pre-Screen + Injection Detector |
| Deployment | Render |
| CI/CD | GitHub Actions |

---

## 📁 Project Structure

- **code/app.py** — Flask web server with premium UI
- **code/agent.py** — Triage agent with all 10 features
- **code/safety.py** — 3-layer security + injection detector
- **code/retriever.py** — BM25 offline retrieval engine
- **code/prompts.py** — LLM prompt engineering
- **code/config.py** — Environment and model configuration
- **code/static/css/** — Premium stylesheets (Aurora, Bento, Auth)
- **data/** — Knowledge base corpus (HackerRank, Claude, Visa)
- **support_tickets/** — Input/output CSV files

---

<div align="center">
  <strong>Made by Saugata Malakar — IIT Kharagpur</strong>
</div>
