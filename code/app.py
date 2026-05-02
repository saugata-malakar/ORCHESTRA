#!/usr/bin/env python3
"""
app.py - Premium 3D Web Dashboard for the Support Triage Agent.
Run: python app.py
Then open http://localhost:5000
"""
import sys, io, os, csv, json, time, random, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
random.seed(42)

from flask import Flask, render_template_string, jsonify, request as flask_request
from config import ANTHROPIC_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, INPUT_CSV, OUTPUT_CSV, TICKETS_DIR
from corpus_loader import load_corpus
from retriever import BM25Retriever
from agent import SupportTriageAgent
from pathlib import Path

app = Flask(__name__)

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

PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Support Triage Agent | HackerRank Orchestrate</title>
<meta name="description" content="AI-powered multi-domain support triage agent for HackerRank, Claude, and Visa">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{--bg:#05060f;--surface:#0c0d1a;--card:#111227;--border:#1c1d3a;--glow:#7c3aed;--cyan:#06b6d4;--pink:#ec4899;--green:#10b981;--red:#ef4444;--amber:#f59e0b;--text:#e2e8f0;--muted:#64748b;--font:'Outfit',sans-serif;}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}

/* 3D Background */
.bg-scene{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none;}
.bg-orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:.15;animation:orbFloat 20s ease-in-out infinite;}
.bg-orb.o1{width:600px;height:600px;background:var(--glow);top:-10%;left:-10%;animation-delay:0s;}
.bg-orb.o2{width:500px;height:500px;background:var(--cyan);bottom:-10%;right:-10%;animation-delay:-7s;}
.bg-orb.o3{width:400px;height:400px;background:var(--pink);top:40%;left:50%;animation-delay:-14s;}
@keyframes orbFloat{0%,100%{transform:translate(0,0) scale(1);}25%{transform:translate(60px,-40px) scale(1.1);}50%{transform:translate(-30px,50px) scale(.9);}75%{transform:translate(40px,20px) scale(1.05);}}

/* Grid lines */
.grid-bg{position:fixed;inset:0;z-index:0;background-image:linear-gradient(rgba(124,58,237,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(124,58,237,.04) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;}

.wrapper{position:relative;z-index:1;}

/* Header */
.header{padding:28px 40px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);backdrop-filter:blur(20px);background:rgba(5,6,15,.7);position:sticky;top:0;z-index:100;}
.logo{display:flex;align-items:center;gap:14px;}
.logo-icon{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,var(--glow),var(--cyan));display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:900;color:#fff;box-shadow:0 0 30px rgba(124,58,237,.4);transform:perspective(400px) rotateY(-8deg);transition:transform .4s;}
.logo-icon:hover{transform:perspective(400px) rotateY(8deg) scale(1.05);}
.logo-text h1{font-size:22px;font-weight:800;background:linear-gradient(135deg,#fff 0%,var(--cyan) 50%,var(--glow) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.logo-text p{font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;}
.header-badge{padding:6px 16px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;border:1px solid var(--border);color:var(--muted);backdrop-filter:blur(10px);}
.header-badge.live{border-color:var(--green);color:var(--green);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,.3);}50%{box-shadow:0 0 0 8px rgba(16,185,129,0);}}

/* Container */
.container{max-width:1440px;margin:0 auto;padding:32px 40px;}

/* Section titles */
.section-title{font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:4px;color:var(--text);margin-bottom:24px;display:flex;align-items:center;gap:12px;text-shadow: 0 0 10px rgba(255,255,255,0.1);}
.section-title::before{content:'';width:30px;height:3px;background:linear-gradient(90deg,var(--glow),var(--cyan));border-radius:2px;box-shadow: 0 0 10px var(--glow);}

/* 3D Stat Cards */
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

/* Control Bar */
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
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.3;}}

/* Panels */
.panels{display:grid;grid-template-columns:1fr 340px;gap:20px;margin-bottom:32px;}

/* Results Table */
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

/* Log Panel */
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

/* About Section & Reading */
.about{display:grid;grid-template-columns:1fr;gap:24px;margin-top:16px;margin-bottom:32px;}
.about-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
.reading-section{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;transform:perspective(800px) rotateX(1deg);transition:all .4s;position:relative;overflow:hidden;}
.reading-section::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--glow),var(--cyan));}
.reading-section:hover{transform:perspective(800px) rotateX(0deg) translateY(-2px);border-color:var(--cyan);box-shadow:0 15px 40px rgba(6,182,212,.15);}
.reading-section h2{font-size:24px;font-weight:900;margin-bottom:16px;background:linear-gradient(135deg,#fff,var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.reading-section p{font-size:15px;color:var(--muted);line-height:1.8;margin-bottom:16px;}
.reading-section ul{list-style:none;padding-left:0;margin-bottom:16px;}
.reading-section ul li{font-size:14px;color:var(--text);margin-bottom:8px;display:flex;align-items:center;gap:10px;}
.reading-section ul li::before{content:'❖';color:var(--glow);font-size:12px;}

.about-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:28px;transform:perspective(600px) rotateX(2deg);transition:all .4s;}
.about-card:hover{transform:perspective(600px) rotateX(-1deg) translateY(-4px);border-color:var(--glow);box-shadow:0 15px 35px rgba(124,58,237,.12);}
.about-card h3{font-size:16px;font-weight:800;margin-bottom:10px;background:linear-gradient(135deg,var(--cyan),var(--glow));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.about-card p{font-size:13px;color:var(--muted);line-height:1.7;}
.about-card .tag{display:inline-block;padding:4px 10px;background:var(--surface);border:1px solid var(--border);border-radius:6px;font-size:11px;color:var(--muted);margin:3px;font-weight:700;letter-spacing:1px;}

/* Footer */
.footer{text-align:center;padding:28px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);margin-top:20px;}

/* Responsive */
@media(max-width:1100px){.panels{grid-template-columns:1fr;}.stats{grid-template-columns:repeat(3,1fr);}}
@media(max-width:700px){.stats{grid-template-columns:repeat(2,1fr);}.about{grid-template-columns:1fr;}.header{padding:16px 20px;}.container{padding:20px;}}
</style>
</head>
<body>
<div class="bg-scene"><div class="bg-orb o1"></div><div class="bg-orb o2"></div><div class="bg-orb o3"></div></div>
<div class="grid-bg"></div>
<div class="wrapper">

<header class="header">
  <div class="logo">
    <div class="logo-icon">ST</div>
    <div class="logo-text">
      <h1>Support Triage Agent</h1>
      <p>HackerRank Orchestrate Hackathon</p>
    </div>
  </div>
  <div id="statusBadge" class="header-badge">Initializing</div>
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

  <div class="section-title">Min-Max Design &amp; Architecture Documentation</div>
  <div class="about">
    <div class="reading-section">
      <h2>Understanding the Triage Engine</h2>
      <p>This application implements a highly optimized, "Min-Max" architectural pattern: <strong>minimizing latency and dependencies</strong> while <strong>maximizing safety and accuracy</strong>. By processing tickets against a custom-built BM25 vectorless index, the system drastically cuts down processing times and overhead costs associated with traditional vector databases.</p>
      <ul>
        <li><strong>Multi-Domain Context:</strong> Contexts are dynamically isolated across HackerRank, Claude, and Visa.</li>
        <li><strong>Rate-Limit Optimization:</strong> Fully automated burst-processing that dynamically backs off only when the Gemini Free Tier 15-RPM quota is hit, minimizing wait times.</li>
        <li><strong>Deterministic RAG:</strong> Temperature is strictly clamped to 0.0 with a fixed 42-seed to ensure absolute reproducibility for support ticket evaluation.</li>
      </ul>
      <p>The UI relies on a 3D glassmorphism approach with hardware-accelerated perspective transforms and floating ambient orbs to create a deeply engaging, tactile experience.</p>
    </div>
    
    <div class="about-grid">
      <div class="about-card">
        <h3>BM25 + RAG Pipeline</h3>
        <p>Offline BM25Okapi retrieval with company-affinity boosting (1.4x) surfaces the most relevant corpus chunks. No vector DB or embeddings required.</p>
        <div style="margin-top:12px"><span class="tag">BM25Okapi</span><span class="tag">Company Boost</span><span class="tag">Top-8 Chunks</span></div>
      </div>
      <div class="about-card">
        <h3>Three-Layer Safety</h3>
        <p>Rule-based pre-screening catches fraud, legal threats, prompt injection, and malicious requests <em>before</em> the LLM. The model adds a fourth layer of judgment.</p>
        <div style="margin-top:12px"><span class="tag">Regex Safety</span><span class="tag">OOS Detection</span><span class="tag">Anti-Injection</span></div>
      </div>
      <div class="about-card">
        <h3>Deterministic Output</h3>
        <p>Temperature=0, random seed=42, and strict JSON schema validation ensure fully reproducible, grounded responses across every run.</p>
        <div style="margin-top:12px"><span class="tag">Temp=0</span><span class="tag">Seed=42</span><span class="tag">JSON Schema</span></div>
      </div>
    </div>
  </div>

</div>

<div class="footer">HackerRank Orchestrate Hackathon 2026 &mdash; Multi-Domain Support Triage &mdash; HackerRank | Claude | Visa</div>

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
    const badge=document.getElementById('statusBadge');
    const label=document.getElementById('progLabel');
    if(d.processing){
      badge.textContent='Processing';badge.className='header-badge live';
      label.innerHTML='<span class="status-dot running"></span>'+d.progress+' / '+d.total;
    }else if(res.length>0){
      badge.textContent='Complete';badge.className='header-badge';badge.style.borderColor='var(--green)';badge.style.color='var(--green)';
      label.innerHTML='<span class="status-dot done"></span>Done ('+res.length+' tickets)';
      clearInterval(polling);polling=null;reenable();
    }else{
      badge.textContent='Ready';badge.className='header-badge';
      label.innerHTML='<span class="status-dot idle"></span>Ready';
    }
    // Table
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
    // Logs
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
// Initial fetch
fetchStatus();setInterval(()=>{if(!polling)fetchStatus();},5000);
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(PAGE)

@app.route('/api/status')
def api_status():
    return jsonify({
        "corpus_loaded":state["corpus_loaded"],"corpus_chunks":state["corpus_chunks"],
        "processing":state["processing"],"progress":state["progress"],
        "total":state["total"],"results":state["results"],
        "log":state["log"][-80:],"has_key":(LLM_PROVIDER != "none"),"error":state["error"],
    })

@app.route('/api/run', methods=['POST'])
def api_run():
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
    print(f"\n  Dashboard: http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
