# Orchestra: Multi-Domain AI Support Triage

![Support Triage Agent](https://img.shields.io/badge/Status-Active-success) ![Gemini](https://img.shields.io/badge/Powered%20By-Google%20Gemini-blue)

**Orchestra** is an ultra-fast, multi-domain AI support triage agent built for the HackerRank Orchestrate Hackathon. It intelligently classifies, screens, and responds to customer support tickets across HackerRank, Claude, and Visa ecosystems.

## 🌟 Key Features
- **Min-Max Architecture**: Achieves extreme low-latency processing without a vector database. Uses a highly optimized offline `BM25Okapi` retrieval system with 1.4x company-affinity boosting.
- **Three-Layer Safety Protocol**: Employs rigorous rule-based regex pre-screening for malicious intents, prompt-injections, and out-of-scope requests *before* the LLM layer.
- **Google Gemini Integration**: Configured with free-tier Gemini API, including an intelligent burst rate-limit handling mechanism for fast throughput.
- **3D Glassmorphism Dashboard**: A premium, visually stunning front-end with real-time logs, live ticket tracking, and interactive stat cards.

## 🚀 Deployment Links
- **Vercel Live URL:** [https://orchestra-saugata-malakar.vercel.app](https://orchestra-saugata-malakar.vercel.app)
- **GitHub Repository:** [https://github.com/saugata-malakar/ORCHESTRA](https://github.com/saugata-malakar/ORCHESTRA)

## 💻 Local Development
1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export your Gemini API key:
   ```powershell
   $env:GEMINI_API_KEY="your_api_key_here"
   ```
3. Run the live 3D web dashboard:
   ```powershell
   cd code
   python app.py
   ```
4. Open `http://localhost:5000` in your browser.

## 🧠 System Internals
The engine is completely deterministic. We clamp the model's temperature to `0.0` with a strict seed, guaranteeing exact reproducibility. When a request is fired, the internal router fetches the top 8 context chunks directly from local memory and feeds them to Gemini in an ultra-strict JSON-bound prompt.
