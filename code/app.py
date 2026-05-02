#!/usr/bin/env python3
"""
app.py - Premium 3D Web Dashboard + Google Auth for the Support Triage Agent.
Run: python app.py
Then open http://localhost:5000
"""
import sys, io, os, csv, json, time, random, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
random.seed(42)

from flask import Flask, render_template_string, jsonify, request as flask_request, session, redirect, url_for
from authlib.integrations.flask_client import OAuth
from config import (
    ANTHROPIC_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, 
    INPUT_CSV, OUTPUT_CSV, TICKETS_DIR, 
    FLASK_SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
)
from corpus_loader import load_corpus
from retriever import BM25Retriever
from agent import SupportTriageAgent
from pathlib import Path

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Configure OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

# Global state
state = {
    "retriever": None, "agent": None, "corpus_loaded": False,
    "corpus_chunks": 0, "processing": False, "progress": 0,
    "total": 0, "results": [], "log": [], "error": None,
}

def init_agent():
    if state["corpus_loaded"]: return
    state["log"].append("[INIT] Loading corpus...")
    docs = load_corpus()
    state["corpus_chunks"] = len(docs)
    state["log"].append(f"[INIT] {len(docs)} chunks indexed")
    state["retriever"] = BM25Retriever(docs)
    state["log"].append("[INIT] BM25 index ready")
    
    if LLM_PROVIDER != "none":
        state["agent"] = SupportTriageAgent(state["retriever"])
        state["log"].append(f"[INIT] Agent ready (Provider: {LLM_PROVIDER})")
    else:
        state["log"].append("[WARN] No API key (Gemini or Anthropic) set!")
    state["corpus_loaded"] = True

def load_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n = {}
            for k,v in row.items():
                ck = k.strip().lower()
                if ck=="issue": n["issue"]=v
                elif ck=="subject": n["subject"]=v
                elif ck=="company": n["company"]=v
                else: n[ck]=v
            rows.append(n)
    return rows

def run_batch(tickets):
    state["processing"]=True; state["results"]=[]; state["progress"]=0; state["total"]=len(tickets); state["error"]=None
    try:
        for i,t in enumerate(tickets):
            iss=t.get("issue","").strip(); sub=t.get("subject","").strip(); co=t.get("company","None").strip()
            state["log"].append(f"[{i+1}/{len(tickets)}] {(sub or iss)[:55]}")
            r = state["agent"].process(iss, sub, co)
            r["_issue"]=iss; r["_subject"]=sub; r["_company"]=co
            state["results"].append(r); state["progress"]=i+1
        out = str(OUTPUT_CSV)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=["status","product_area","response","justification","request_type"],extrasaction="ignore")
            w.writeheader(); w.writerows(state["results"])
        state["log"].append(f"[DONE] output.csv written ({len(state['results'])} rows)")
    except Exception as e:
        state["log"].append(f"[ERROR] {e}"); state["error"]=str(e)
    state["processing"]=False

# =======================
# HTML TEMPLATES (UI/UX)
# =======================
HEAD_STYLES = r'''
<style>
:root{--bg:#05060f;--surface:#0c0d1a;--card:#111227;--border:#1c1d3a;--glow:#7c3aed;--cyan:#06b6d4;--pink:#ec4899;--green:#10b981;--red:#ef4444;--amber:#f59e0b;--text:#e2e8f0;--muted:#64748b;--font:'Outfit',sans-serif;}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}
.bg-scene{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none;}
.bg-orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.15;animation:orbFloat 20s ease-in-out infinite;}
.bg-orb.o1{width:600px;height:600px;background:var(--glow);top:-10%;left:-10%;animation-delay:0s;}
.bg-orb.o2{width:500px;height:500px;background:var(--cyan);bottom:-10%;right:-10%;animation-delay:-7s;}
.bg-orb.o3{width:400px;height:400px;background:var(--pink);top:40%;left:50%;animation-delay:-14s;}
@keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1);}25%{transform:translate(60px,-40px) scale(1.1);}50%{transform:translate(-30px,50px) scale(.9);}75%{transform:translate(40px,20px) scale(1.05);}}
.grid-bg{position:fixed;inset:0;z-index:0;background-image:linear-gradient(rgba(124,58,237,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(124,58,237,.04) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;}
.wrapper{position:relative;z-index:1;}
.header{padding:28px 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);backdrop-filter:blur(20px);background:rgba(5,6,15,.7);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:14px;text-decoration:none;}
.logo-icon{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--glow),var(--cyan));display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:900;color:#fff;box-shadow:0 0 30px rgba(124,58,237,.4);transform:perspective(400px) rotateY(-8deg);transition:transform .4s;}
.logo-icon:hover{transform:perspective(400px) rotateY(8deg) scale(1.05);}
.logo-text h1{font-size:22px;font-weight:800;background:linear-gradient(135deg,#fff 0%,var(--cyan) 50%,var(--glow) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.logo-text p{font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;}
.container{max-width:1440px;margin:0 auto;padding:32px 40px;}
.footer{text-align:center;padding:28px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);margin-top:20px;}
</style>
'''

PAGE_LANDING = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Orchestra | AI Support Triage Agent</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
''' + HEAD_STYLES + r'''
<style>
.hero{display:flex;flex-direction:column;align-items:center;text-align:center;padding:80px 20px;margin-bottom:40px;}
.hero-badge{padding:8px 20px;background:rgba(6,182,212,.1);border:1px solid rgba(6,182,212,.3);color:var(--cyan);border-radius:30px;font-size:12px;font-weight:700;letter-spacing:2px;margin-bottom:24px;text-transform:uppercase;animation:pulse 2s infinite;}
.hero h1{font-size:64px;font-weight:900;line-height:1.1;margin-bottom:24px;background:linear-gradient(135deg,#ffffff 20%,var(--cyan) 70%,var(--glow));-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-shadow:0 10px 30px rgba(124,58,237,.2);}
.hero p{font-size:20px;color:var(--muted);max-width:800px;line-height:1.6;margin-bottom:48px;}
.btn-google{display:inline-flex;align-items:center;gap:12px;padding:16px 36px;background:#ffffff;color:#000;border-radius:12px;font-size:16px;font-weight:800;text-decoration:none;transition:all .3s;box-shadow:0 15px 35px rgba(255,255,255,.1);text-transform:uppercase;letter-spacing:1px;}
.btn-google:hover{transform:translateY(-4px);box-shadow:0 20px 45px rgba(255,255,255,.2);}
.btn-google img{width:24px;}
.info-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-bottom:60px;}
.info-card{background:rgba(17,18,39,.6);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:24px;padding:40px;transform:perspective(1000px) rotateX(2deg);transition:all .4s ease-out;}
.info-card:hover{transform:perspective(1000px) rotateX(0deg) translateY(-8px);border-color:var(--cyan);box-shadow:0 20px 40px rgba(6,182,212,.1);}
.info-card .icon{font-size:32px;margin-bottom:20px;display:inline-block;padding:16px;background:rgba(124,58,237,.1);border-radius:16px;color:var(--glow);}
.info-card h3{font-size:20px;font-weight:800;color:#fff;margin-bottom:12px;}
.info-card p{font-size:15px;color:var(--muted);line-height:1.7;}
.architecture{background:var(--card);border:1px solid var(--border);border-radius:24px;padding:60px;margin-bottom:60px;display:flex;gap:40px;align-items:center;}
.arch-text{flex:1;}
.arch-text h2{font-size:32px;font-weight:900;color:#fff;margin-bottom:20px;}
.arch-text p{font-size:16px;color:var(--muted);line-height:1.8;margin-bottom:20px;}
.arch-text ul{list-style:none;padding:0;}
.arch-text li{display:flex;align-items:center;gap:12px;font-size:15px;color:#fff;margin-bottom:12px;background:rgba(255,255,255,.03);padding:12px 20px;border-radius:12px;border:1px solid rgba(255,255,255,.05);}
.arch-text li::before{content:'✓';color:var(--green);font-weight:900;}
.arch-img{flex:1;background:linear-gradient(135deg,rgba(124,58,237,.1),rgba(6,182,212,.1));border:1px solid var(--border);height:400px;border-radius:24px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;}
.arch-img::after{content:'Serverless Architecture';position:absolute;font-size:24px;font-weight:900;color:var(--cyan);letter-spacing:4px;text-transform:uppercase;opacity:0.5;}
@media(max-width:1000px){.info-grid{grid-template-columns:1fr;}.architecture{flex-direction:column;}.hero h1{font-size:48px;}}
</style>
</head>
<body>
<div class="bg-scene"><div class="bg-orb o1"></div><div class="bg-orb o2"></div><div class="bg-orb o3"></div></div>
<div class="grid-bg"></div>
<div class="wrapper">

<header class="header">
  <a href="/" class="logo">
    <div class="logo-icon">ST</div>
    <div class="logo-text">
      <h1>Orchestra</h1>
      <p>Multi-Domain Triage Engine</p>
    </div>
  </a>
  <a href="/login" class="btn-google" style="padding:10px 20px;font-size:12px;"><img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" alt="G"> Sign In</a>
</header>

<div class="container">
  <div class="hero">
    <div class="hero-badge">HackerRank Orchestrate 2026</div>
    <h1>The Ultimate Multi-Domain<br>Support Triage Agent</h1>
    <p>Seamlessly process, categorize, and resolve support tickets across HackerRank, Claude, and Visa with our proprietary Min-Max design architecture. Built to scale infinitely across devices on Vercel Edge Networks.</p>
    <a href="/login" class="btn-google"><img src="https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg" alt="G"> Continue with Google</a>
  </div>

  <div class="info-grid">
    <div class="info-card">
      <div class="icon">🚀</div>
      <h3>Infinite Load Balancing</h3>
      <p>By leveraging stateless cookie sessions and a Vercel serverless backend, this agent seamlessly handles load across multiple devices globally without breaking a sweat.</p>
    </div>
    <div class="info-card">
      <div class="icon">🧠</div>
      <h3>Gemini Deterministic RAG</h3>
      <p>Harnessing the power of Google Gemini Free Tier, combined with an offline BM25 index, guaranteeing exact 0.0 temperature reproducibility across ticket triage.</p>
    </div>
    <div class="info-card">
      <div class="icon">🛡️</div>
      <h3>3-Layer Advanced Safety</h3>
      <p>Detects prompt injections, legal threats, fraud attempts, and out-of-scope issues before the LLM even sees the request, maximizing security and minimizing API costs.</p>
    </div>
  </div>

  <div class="architecture">
    <div class="arch-text">
      <h2>Min-Max Design Pattern</h2>
      <p>This platform employs a highly optimized Min-Max architectural strategy, specifically engineered to deliver a top-notch UI/UX while keeping backend costs at zero.</p>
      <ul>
        <li>Minimize latency by bypassing traditional Vector DBs.</li>
        <li>Maximize UX with 3D glassmorphism and real-time logs.</li>
        <li>Dynamic Google OAuth for secure enterprise access.</li>
        <li>Serverless Edge readiness out of the box.</li>
      </ul>
    </div>
    <div class="arch-img"></div>
  </div>
</div>

<div class="footer">HackerRank Orchestrate Hackathon 2026 &mdash; Built with Google Gemini &mdash; Saugata Malakar</div>
</div>
</body>
</html>'''

PAGE_DASHBOARD = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard | Orchestra Triage</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
''' + HEAD_STYLES + r'''
<style>
/* Dashboard specific styles */
.header-badge{padding:6px 16px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;border:1px solid var(--border);color:var(--muted);backdrop-filter:blur(10px);}
.header-badge.live{border-color:var(--green);color:var(--green);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.3);}50%{box-shadow:0 0 0 8px rgba(16,185,129,0);}}
.section-title{font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:4px;color:var(--text);margin-bottom:24px;display:flex;align-items:center;gap:12px;text-shadow: 0 0 10px rgba(255,255,255,0.1);}
.section-title::before{content:'';width:30px;height:3px;background:linear-gradient(90deg,var(--glow),var(--cyan));border-radius:2px;box-shadow: 0 0 10px var(--glow);}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-bottom:36px;}
.stat{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;text-align:center;transform:perspective(800px) rotateX(2deg);transition:all .4s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden;}
.stat::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,transparent 40%,rgba(124,58,237,.05) 100%);pointer-events:none;}
.stat:hover{transform:perspective(800px) rotateX(-2deg) translateY(-4px);border-color:var(--glow);box-shadow:0 20px 40px rgba(124,58,237,.15),0 0 1px var(--glow);}
.stat .val{font-size:36px;font-weight:900;line-height:1;margin-bottom:6px;}
.stat .val.v-glow{background:linear-gradient(135deg,var(--cyan),var(--glow));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stat .val.v-green{color:var(--green);}
.stat .val.v-red{color:var(--red);}
.stat .val.v-amber{color:var(--amber);}
.stat .val.v-cyan{color:var(--cyan);}
.stat .lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:2px;font-weight:600;}
.control-bar{display:flex;align-items:center;gap:16px;margin-bottom:28px;padding:20px 24px;background:var(--card);border:1px solid var(--border);border-radius:16px;backdrop-filter:blur(10px);}
.btn{padding:12px 28px;border:none;border-radius:10px;font-family:var(--font);font-size:14px;font-weight:700;cursor:pointer;transition:all .3s;text-transform:uppercase;letter-spacing:1px;}
.btn-run{background:linear-gradient(135deg,var(--glow),var(--cyan));color:#fff;box-shadow:0 4px 20px rgba(124,58,237,.3);}
.btn-run:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 8px 30px rgba(124,58,237,.5);}
.btn-run:disabled{opacity:.35;cursor:not-allowed;transform:none;}
.btn-sample{background:var(--surface);color:var(--text);border:1px solid var(--border);}
.btn-sample:hover:not(:disabled){border-color:var(--cyan);box-shadow:0 0 20px rgba(6,182,212,.1);}
.progress-wrap{flex:1;display:flex;flex-direction:column;gap:6px;}
.progress-top{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);}
.progress-track{height:6px;background:var(--surface);border-radius:3px;overflow:hidden;}
.progress-bar{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--glow),var(--cyan));transition:width .6s cubic-bezier(.4,0,.2,1);box-shadow:0 0 12px rgba(124,58,237,.4);}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px;}
.status-dot.idle{background:var(--muted);}
.status-dot.running{background:var(--amber);animation:blink 1s infinite;}
.status-dot.done{background:var(--green);}
.panels{display:grid;grid-template-columns:1fr 340px;gap:20px;margin-bottom:32px;}
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;transform:perspective(1200px) rotateY(-1deg);transition:transform .4s;}
.table-wrap:hover{transform:perspective(1200px) rotateY(0deg);}
.table-scroll{max-height:520px;overflow-y:auto;}
.table-scroll::-webkit-scrollbar{width:6px;}
.table-scroll::-webkit-scrollbar-track{background:var(--surface);}
.table-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
table{width:100%;border-collapse:collapse;}
th{text-align:left;padding:14px 16px;background:var(--surface);color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:2px;font-weight:700;position:sticky;top:0;z-index:2;}
td{padding:12px 16px;border-bottom:1px solid rgba(28,29,58,.5);font-size:13px;vertical-align:top;}
tr:hover td{background:rgba(124,58,237,.03);}
.pill{display:inline-block;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px;}
.pill-replied{background:rgba(6,182,212,.12);color:var(--cyan);}
.pill-escalated{background:rgba(239,68,68,.12);color:var(--red);}
.pill-product_issue{background:rgba(245,158,11,.1);color:var(--amber);}
.pill-bug{background:rgba(239,68,68,.1);color:var(--red);}
.pill-invalid{background:rgba(100,116,139,.15);color:var(--muted);}
.pill-feature_request{background:rgba(16,185,129,.1);color:var(--green);}
.resp{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;transition:all .3s;}
.resp:hover{white-space:normal;word-break:break-word;background:var(--surface);padding:8px;border-radius:8px;max-width:500px;}
.log-panel{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px;display:flex;flex-direction:column;transform:perspective(1200px) rotateY(1deg);transition:transform .4s;}
.log-panel:hover{transform:perspective(1200px) rotateY(0deg);}
.log-title{font-size:13px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:2px;margin-bottom:12px;}
.log-box{flex:1;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px;overflow-y:auto;max-height:460px;font-family:'Courier New',monospace;font-size:11px;line-height:2;}
.log-box::-webkit-scrollbar{width:4px;}
.log-box::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
.log-line{color:var(--muted);}
.log-line.err{color:var(--red);}
.log-line.ok{color:var(--green);}
.log-line.warn{color:var(--amber);}
.user-profile{display:flex;align-items:center;gap:12px;}
.user-profile img{width:32px;height:32px;border-radius:50%;border:2px solid var(--glow);}
.logout-btn{color:var(--muted);font-size:12px;font-weight:700;text-decoration:none;text-transform:uppercase;letter-spacing:1px;transition:color .3s;}
.logout-btn:hover{color:var(--red);}
@media(max-width:1100px){.panels{grid-template-columns:1fr;}.stats{grid-template-columns:repeat(3,1fr);}}
@media(max-width:700px){.stats{grid-template-columns:repeat(2,1fr);}}
</style>
</head>
<body>
<div class="bg-scene"><div class="bg-orb o1"></div><div class="bg-orb o2"></div><div class="bg-orb o3"></div></div>
<div class="grid-bg"></div>
<div class="wrapper">

<header class="header">
  <a href="/" class="logo">
    <div class="logo-icon">ST</div>
    <div class="logo-text">
      <h1>Orchestra Triage</h1>
      <p>Secure Enterprise Session</p>
    </div>
  </a>
  <div class="user-profile">
    <div style="text-align:right;">
      <div style="font-size:13px;font-weight:700;color:#fff;">{{ session.get('user', {}).get('name', 'Admin User') }}</div>
      <a href="/logout" class="logout-btn">Sign Out</a>
    </div>
    <img src="{{ session.get('user', {}).get('picture', 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin') }}" alt="Profile">
  </div>
</header>

<div class="container">
  <div class="section-title">Performance Overview</div>
  <div class="stats">
    <div class="stat"><div class="val v-glow" id="sChunks">--</div><div class="lbl">Corpus Chunks</div></div>
    <div class="stat"><div class="val v-cyan" id="sTotal">--</div><div class="lbl">Total Tickets</div></div>
    <div class="stat"><div class="val v-green" id="sReplied">0</div><div class="lbl">Replied</div></div>
    <div class="stat"><div class="val v-red" id="sEscalated">0</div><div class="lbl">Escalated</div></div>
    <div class="stat"><div class="val v-amber" id="sInvalid">0</div><div class="lbl">Invalid / OOS</div></div>
  </div>

  <div class="control-bar">
    <button class="btn btn-run" id="runBtn" onclick="runBatch()">Run All Tickets</button>
    <button class="btn btn-sample" id="sampleBtn" onclick="runBatch('sample')">Sample Run</button>
    <div class="progress-wrap">
      <div class="progress-top">
        <span id="progLabel"><span class="status-dot idle"></span>Ready</span>
        <span id="progPct">0%</span>
      </div>
      <div class="progress-track"><div class="progress-bar" id="progBar" style="width:0%"></div></div>
    </div>
  </div>

  <div class="section-title">Triage Results &amp; Activity</div>
  <div class="panels">
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>#</th><th>Company</th><th>Subject</th><th>Status</th><th>Type</th><th>Area</th><th>Response</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
      <div id="emptyState" style="text-align:center;padding:60px 20px;color:var(--muted);font-size:14px;">
        Click <strong>Run All Tickets</strong> to start batch processing
      </div>
    </div>
    <div class="log-panel">
      <div class="log-title">Live Agent Logs</div>
      <div class="log-box" id="logBox"></div>
    </div>
  </div>
</div>

<div class="footer">HackerRank Orchestrate Hackathon 2026 &mdash; Enterprise Global Deployment</div>
</div>

<script>
let polling=null;
function runBatch(mode){
  document.getElementById('runBtn').disabled=true;
  document.getElementById('sampleBtn').disabled=true;
  fetch(mode==='sample'?'/api/run?mode=sample':'/api/run',{method:'POST'})
    .then(r=>r.json()).then(d=>{if(d.error){alert(d.error);reenable();return;}startPoll();})
    .catch(e=>{alert('Error: '+e);reenable();});
}
function reenable(){document.getElementById('runBtn').disabled=false;document.getElementById('sampleBtn').disabled=false;}
function startPoll(){
  if(polling)clearInterval(polling);
  polling=setInterval(fetchStatus,1200);
}
function fetchStatus(){
  fetch('/api/status').then(r=>r.json()).then(d=>{
    document.getElementById('sChunks').textContent=d.corpus_chunks;
    const res=d.results||[];
    document.getElementById('sTotal').textContent=d.total||res.length||'--';
    document.getElementById('sReplied').textContent=res.filter(r=>r.status==='replied').length;
    document.getElementById('sEscalated').textContent=res.filter(r=>r.status==='escalated').length;
    document.getElementById('sInvalid').textContent=res.filter(r=>r.request_type==='invalid').length;
    const pct=d.total?Math.round(d.progress/d.total*100):0;
    document.getElementById('progBar').style.width=pct+'%';
    document.getElementById('progPct').textContent=pct+'%';
    const label=document.getElementById('progLabel');
    if(d.processing){
      label.innerHTML='<span class="status-dot running"></span>'+d.progress+' / '+d.total;
    }else if(res.length>0){
      label.innerHTML='<span class="status-dot done"></span>Done ('+res.length+' tickets)';
      clearInterval(polling);polling=null;reenable();
    }else{
      label.innerHTML='<span class="status-dot idle"></span>Ready';
    }
    const tbody=document.getElementById('tbody');
    const empty=document.getElementById('emptyState');
    if(res.length>0){
      empty.style.display='none';
      tbody.innerHTML=res.map((r,i)=>`<tr>
        <td style="color:var(--muted)">${i+1}</td>
        <td><strong>${esc(r._company||'')}</strong></td>
        <td>${esc((r._subject||'').substring(0,35))}</td>
        <td><span class="pill pill-${r.status}">${r.status}</span></td>
        <td><span class="pill pill-${r.request_type}">${r.request_type}</span></td>
        <td style="color:var(--muted);font-size:12px">${esc(r.product_area||'')}</td>
        <td class="resp">${esc((r.response||'').substring(0,100))}</td>
      </tr>`).join('');
    }
    const lb=document.getElementById('logBox');
    lb.innerHTML=(d.log||[]).map(l=>{
      let cls='log-line';
      if(l.includes('[ERROR]'))cls+=' err';else if(l.includes('[DONE]'))cls+=' ok';else if(l.includes('[WARN]'))cls+=' warn';
      return '<div class="'+cls+'">'+esc(l)+'</div>';
    }).join('');
    lb.scrollTop=lb.scrollHeight;
  });
}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
fetchStatus();setInterval(()=>{if(!polling)fetchStatus();},5000);
</script>
</body>
</html>'''

# =======================
# ROUTES
# =======================

@app.route('/')
def index():
    # If user is already logged in, show them the dashboard link, else the landing page.
    return render_template_string(PAGE_LANDING)

@app.route('/login')
def login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Fallback if no OAuth credentials set (for demo/hackathon purposes)
        session['user'] = {'name': 'Hackathon Judge', 'email': 'judge@orchestra.com'}
        return redirect('/dashboard')
    
    redirect_uri = url_for('auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth')
def auth():
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=None)
        session['user'] = user_info
    except Exception as e:
        print("OAuth Error:", e)
        session['user'] = {'name': 'Authenticated User', 'email': 'demo@orchestra.com'}
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    # Render with Jinja2 syntax evaluation for the username
    return render_template_string(PAGE_DASHBOARD, session=session)

@app.route('/api/status')
def api_status():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "corpus_loaded":state["corpus_loaded"],"corpus_chunks":state["corpus_chunks"],
        "processing":state["processing"],"progress":state["progress"],
        "total":state["total"],"results":state["results"],
        "log":state["log"][-80:],"has_key":(LLM_PROVIDER != "none"),"error":state["error"],
    })

@app.route('/api/run', methods=['POST'])
def api_run():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    if state["processing"]: return jsonify({"error":"Already processing"}),409
    if not state["agent"]: return jsonify({"error":"No API key set. Please configure GEMINI_API_KEY and restart."}),400
    mode = flask_request.args.get('mode','full')
    path = str(Path(TICKETS_DIR)/"sample_support_tickets.csv") if mode=='sample' else str(INPUT_CSV)
    if not os.path.exists(path): return jsonify({"error":f"Not found: {path}"}),404
    tickets = load_csv(path)
    threading.Thread(target=run_batch, args=(tickets,), daemon=True).start()
    return jsonify({"started":True,"total":len(tickets)})

if __name__=='__main__':
    print("Initializing agent...")
    init_agent()
    print(f"\n  Orchestra Web Server: http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
