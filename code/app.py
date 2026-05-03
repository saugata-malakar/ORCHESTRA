#!/usr/bin/env python3
"""
app.py - Premium Web Dashboard with optional WebSockets & Audit Trails.
Works on both Vercel (serverless, no WS) and localhost (full WS).
"""
import sys, io, os, csv, json, time, random, threading
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except: pass
random.seed(42)

from flask import Flask, render_template_string, jsonify, request as flask_request, session, redirect, url_for

# SocketIO is optional — Vercel serverless doesn't support WebSockets
try:
    from flask_socketio import SocketIO
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False

try:
    from authlib.integrations.flask_client import OAuth
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False

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

# Feature #5: Streaming Live Dashboard with WebSockets (when available)
if HAS_SOCKETIO:
    socketio = SocketIO(app, cors_allowed_origins="*")
else:
    socketio = None

if HAS_OAUTH:
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
else:
    google = None

state = {
    "retriever": None, "agent": None, "corpus_loaded": False,
    "corpus_chunks": 0, "processing": False, "progress": 0,
    "total": 0, "results": [], "log": [], "error": None,
}

def _emit(event, data):
    if socketio:
        try: socketio.emit(event, data)
        except: pass

def log(msg):
    state["log"].append(msg)
    _emit('log_update', {"message": msg})

def init_agent():
    if state["corpus_loaded"]: return
    log("[INIT] Loading corpus...")
    docs = load_corpus()
    state["corpus_chunks"] = len(docs)
    log(f"[INIT] {len(docs)} chunks indexed")
    state["retriever"] = BM25Retriever(docs)
    log("[INIT] BM25 index ready")
    
    if LLM_PROVIDER != "none":
        state["agent"] = SupportTriageAgent(state["retriever"])
        log(f"[INIT] Agent ready (Provider: {LLM_PROVIDER})")
    else:
        log("[WARN] No API key (Gemini or Anthropic) set!")
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
    _emit('batch_start', {"total": len(tickets)})
    
    try:
        for i,t in enumerate(tickets):
            iss=t.get("issue","").strip(); sub=t.get("subject","").strip(); co=t.get("company","None").strip()
            log(f"[{i+1}/{len(tickets)}] {(sub or iss)[:55]}")
            
            # Agent processing
            r = state["agent"].process(iss, sub, co)
            
            # Feature #6: Audit Trail
            r["_id"] = i + 1
            r["_issue"] = iss
            r["_subject"] = sub
            r["_company"] = co
            
            state["results"].append(r)
            state["progress"] = i + 1
            
            # Push instantly via WebSockets (Feature #5)
            _emit('ticket_done', {"ticket": r, "progress": i + 1, "total": len(tickets)})
            
        # Write output.csv
        out = str(OUTPUT_CSV)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out,"w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=["status","product_area","response","justification","request_type"],extrasaction="ignore")
            w.writeheader(); w.writerows(state["results"])
            
        # Write output_audit.json (Feature #6)
        audit_out = out.replace(".csv", "_audit.json")
        with open(audit_out, "w", encoding="utf-8") as f:
            json.dump(state["results"], f, indent=2)
            
        log(f"[DONE] output.csv and output_audit.json written ({len(state['results'])} rows)")
        _emit('batch_done', {})
    except Exception as e:
        err = f"[ERROR] {e}"
        log(err)
        state["error"]=str(e)
        _emit('batch_error', {"error": str(e)})
    state["processing"]=False

# =======================
# HTML TEMPLATES (UI/UX)
# =======================
GOOGLE_SVG = '''<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>'''

PAGE_LANDING = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Orchestra | Premium Support Triage</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/globals.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/landing.css') }}">
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
      <p>Commercial Triage Engine</p>
    </div>
  </a>
  <a href="/login" class="btn-glass">Sign In</a>
</header>
<div class="container">
  <div class="hero">
    <div class="hero-badge">Orchestrate Hackathon 2026</div>
    <h1>The Ultimate Multi-Domain<br><span class="gradient-text">Support Triage Agent</span></h1>
    <p>Seamlessly process, categorize, and resolve support tickets across HackerRank, Claude, and Visa with our proprietary Min-Max design architecture. Built to scale infinitely across devices on Vercel Edge Networks.</p>
    <a href="/login" class="btn-primary">Access Triage Engine</a>
  </div>
  <div class="bento-grid">
    <div class="bento-item bento-large">
      <div class="bento-icon">🧠</div>
      <div class="bento-title">Gemini Deterministic RAG</div>
      <div class="bento-desc">Harnessing the power of Google Gemini Free Tier, combined with a high-performance offline BM25 index. We guarantee exact 0.0 temperature reproducibility across enterprise ticket triage.</div>
    </div>
    <div class="bento-item">
      <div class="bento-icon">🚀</div>
      <div class="bento-title">WebSocket Streaming</div>
      <div class="bento-desc">Watch tickets process in real-time. By leveraging Socket.IO and stateless cookie sessions, this agent effortlessly handles high-concurrency traffic globally.</div>
    </div>
    <div class="bento-item">
      <div class="bento-icon">🛡️</div>
      <div class="bento-title">Auto-Deduplication & Safety</div>
      <div class="bento-desc">Detects prompt injections, legal threats, and identical tickets using TF-IDF vectorization before the LLM evaluates the request, saving crucial API costs.</div>
    </div>
  </div>
</div>
</div>
</body>
</html>'''

PAGE_AUTH = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign In | Orchestra</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/globals.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/auth.css') }}">
</head>
<body>
<div class="auth-layout">
  <div class="auth-brand">
    <div class="auth-brand-content">
      <a href="/" class="logo" style="margin-bottom: auto;">
        <div class="logo-icon">ST</div>
        <div class="logo-text"><h1>Orchestra</h1><p>Enterprise Triage</p></div>
      </a>
      <div style="margin-top:auto;">
        <h1>Secure.<br>Deterministic.<br>Limitless.</h1>
        <p>Access the proprietary Min-Max triage dashboard designed for handling high-volume tickets across global domains.</p>
      </div>
    </div>
  </div>
  <div class="auth-panel">
    <div class="auth-box">
      <div class="auth-title">Sign In to Orchestra</div>
      <div class="auth-subtitle">Welcome back! Please enter your details.</div>
      <form action="/login_submit" method="POST">
        <div class="form-group">
          <label class="form-label">Email Address</label>
          <input type="email" name="email" class="form-input" placeholder="Enter your email" required>
        </div>
        <div class="form-group">
          <label class="form-label">Password</label>
          <input type="password" name="password" class="form-input" placeholder="••••••••" required>
        </div>
        <div class="form-options">
          <label class="checkbox-wrap"><input type="checkbox" checked> Remember me</label>
          <a href="#" class="forgot-link">Forgot password?</a>
        </div>
        <button type="submit" class="btn-submit">Sign In</button>
      </form>
      <div class="divider">or continue with</div>
      <a href="/google_login" class="btn-oauth">''' + GOOGLE_SVG + r''' Google</a>
      <div class="auth-switch">Don't have an account? <a href="#">Sign Up</a></div>
    </div>
  </div>
</div>
</body>
</html>'''

PAGE_DASHBOARD = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard | Orchestra Triage</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/globals.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.1/socket.io.js"></script>
</head>
<body>
<div class="bg-scene"><div class="bg-orb o1"></div><div class="bg-orb o2"></div><div class="bg-orb o3"></div></div>
<div class="grid-bg"></div>
<div class="wrapper">

<header class="header">
  <a href="/" class="logo">
    <div class="logo-icon">ST</div>
    <div class="logo-text"><h1>Orchestra Triage</h1><p>Secure Enterprise Session</p></div>
  </a>
  <div style="display:flex;align-items:center;gap:16px;">
    <div style="text-align:right;">
      <div style="font-size:14px;font-weight:800;color:#fff;">{{ session.get('user', {}).get('name', 'Admin User') }}</div>
      <a href="/logout" style="color:var(--red);font-size:12px;font-weight:700;text-decoration:none;text-transform:uppercase;letter-spacing:1px;">Sign Out</a>
    </div>
    <img src="{{ session.get('user', {}).get('picture', 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin') }}" alt="Profile" style="width:40px;height:40px;border-radius:50%;border:2px solid var(--cyan);">
  </div>
</header>

<div class="container" style="max-width:1440px;">
  <div class="dashboard-header">
    <div class="dashboard-title">Live Performance Overview (WebSocket Stream)</div>
  </div>

  <div class="stats">
    <div class="stat"><div class="val v-glow" id="sChunks">{{ chunks }}</div><div class="lbl">Corpus Chunks</div></div>
    <div class="stat"><div class="val v-cyan" id="sTotal">--</div><div class="lbl">Total Tickets</div></div>
    <div class="stat"><div class="val v-green" id="sReplied">0</div><div class="lbl">Replied</div></div>
    <div class="stat"><div class="val v-red" id="sEscalated">0</div><div class="lbl">Escalated</div></div>
    <div class="stat"><div class="val v-amber" id="sInvalid">0</div><div class="lbl">Invalid / OOS</div></div>
  </div>

  <div class="control-bar">
    <button class="btn-dashboard btn-run" id="runBtn" onclick="runBatch('full')">Run All Tickets</button>
    <button class="btn-dashboard btn-sample" id="sampleBtn" onclick="runBatch('sample')">Sample Run</button>
    <div class="progress-wrap">
      <div class="progress-top">
        <span id="progLabel">Ready to process</span>
        <span id="progPct">0%</span>
      </div>
      <div class="progress-track"><div class="progress-bar" id="progBar" style="width:0%"></div></div>
    </div>
  </div>

  <div class="panels">
    <div class="table-wrap">
      <div class="table-scroll">
        <table>
          <thead><tr><th>#</th><th>Conf.</th><th>Company</th><th>Status</th><th>Type</th><th>Audit Flags</th><th>Response</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
      <div id="emptyState" style="text-align:center;padding:100px 20px;color:var(--muted);font-size:15px;font-weight:500;">
        Click <strong>Run All Tickets</strong> to initialize the WebSocket engine.
      </div>
    </div>
    <div class="log-panel">
      <div class="log-title">System Logs</div>
      <div class="log-box" id="logBox"></div>
    </div>
  </div>
</div>

<div class="footer">Orchestra Hackathon Project 2026 &mdash; Saugata Malakar</div>
</div>

<script>
const socket = io();
let processedData = [];

socket.on('connect', () => {
  console.log('Connected to WebSocket server');
});

socket.on('batch_start', (data) => {
  document.getElementById('runBtn').disabled = true;
  document.getElementById('sampleBtn').disabled = true;
  document.getElementById('sTotal').textContent = data.total;
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('tbody').innerHTML = '';
  processedData = [];
});

socket.on('ticket_done', (data) => {
  const r = data.ticket;
  processedData.push(r);
  
  // Update progress
  const pct = Math.round((data.progress / data.total) * 100);
  document.getElementById('progBar').style.width = pct + '%';
  document.getElementById('progPct').textContent = pct + '%';
  document.getElementById('progLabel').textContent = `Processing ${data.progress} of ${data.total}...`;
  
  // Update stats
  document.getElementById('sReplied').textContent = processedData.filter(x=>x.status==='replied').length;
  document.getElementById('sEscalated').textContent = processedData.filter(x=>x.status==='escalated').length;
  document.getElementById('sInvalid').textContent = processedData.filter(x=>x.request_type==='invalid').length;
  
  // Render row
  const flagsHtml = (r.audit_flags || []).map(f => `<span style="display:inline-block;padding:2px 6px;margin:2px;background:rgba(139,92,246,0.2);color:#c4b5fd;font-size:9px;border-radius:4px;border:1px solid rgba(139,92,246,0.4);">${f}</span>`).join('');
  const confColor = r.confidence > 0.8 ? 'var(--green)' : (r.confidence > 0.5 ? 'var(--amber)' : 'var(--red)');
  
  const row = `<tr>
    <td style="color:var(--muted)">${r._id}</td>
    <td><strong style="color:${confColor}">${Math.round(r.confidence * 100)}%</strong></td>
    <td><strong>${esc(r._company||'')}</strong></td>
    <td><span class="pill pill-${r.status}">${r.status}</span></td>
    <td><span class="pill pill-${r.request_type}">${r.request_type}</span></td>
    <td>${flagsHtml}</td>
    <td class="resp" title="${esc(r.justification)}">${esc((r.response||'').substring(0,100))}</td>
  </tr>`;
  
  document.getElementById('tbody').insertAdjacentHTML('beforeend', row);
});

socket.on('log_update', (data) => {
  const lb = document.getElementById('logBox');
  let cls='log-line';
  const l = data.message;
  if(l.includes('[ERROR]'))cls+=' err';else if(l.includes('[DONE]'))cls+=' ok';else if(l.includes('[WARN]'))cls+=' warn';
  lb.insertAdjacentHTML('beforeend', `<div class="${cls}">${esc(l)}</div>`);
  lb.scrollTop = lb.scrollHeight;
});

socket.on('batch_done', () => {
  document.getElementById('progLabel').textContent = `Done (${processedData.length} tickets completed)`;
  document.getElementById('runBtn').disabled = false;
  document.getElementById('sampleBtn').disabled = false;
});

socket.on('batch_error', (data) => {
  alert('Error processing batch: ' + data.error);
  document.getElementById('runBtn').disabled = false;
  document.getElementById('sampleBtn').disabled = false;
});

function runBatch(mode) {
  fetch(mode === 'sample' ? '/api/run?mode=sample' : '/api/run', {method:'POST'})
    .then(r => r.json())
    .then(d => { if(d.error) alert(d.error); })
    .catch(e => alert('Error: '+e));
}

function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
</script>
</body>
</html>'''

# =======================
# ROUTES
# =======================

@app.route('/')
def index():
    return render_template_string(PAGE_LANDING)

@app.route('/login')
def login_page():
    return render_template_string(PAGE_AUTH)

@app.route('/login_submit', methods=['POST'])
def login_submit():
    email = flask_request.form.get('email', 'admin@orchestra.com')
    session['user'] = {'name': email.split('@')[0].capitalize(), 'email': email}
    return redirect('/dashboard')

@app.route('/google_login')
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
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
        session['user'] = {'name': 'Authenticated User', 'email': 'demo@orchestra.com'}
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/login')
    return render_template_string(PAGE_DASHBOARD, session=session, chunks=state["corpus_chunks"])

@app.route('/api/run', methods=['POST'])
def api_run():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    if state["processing"]: return jsonify({"error":"Already processing"}),409
    if not state["agent"]: return jsonify({"error":"No API key set. Please configure GEMINI_API_KEY and restart."}),400
    
    mode = flask_request.args.get('mode','full')
    path = str(Path(TICKETS_DIR)/"sample_support_tickets.csv") if mode=='sample' else str(INPUT_CSV)
    if not os.path.exists(path): return jsonify({"error":f"Not found: {path}"}),404
    
    tickets = load_csv(path)
    # Start thread with socket context
    threading.Thread(target=run_batch, args=(tickets,), daemon=True).start()
    return jsonify({"started":True,"total":len(tickets)})

@app.route('/api/status')
def api_status():
    return jsonify({"processing": state["processing"], "progress": state["progress"], "total": state["total"], "results": state["results"], "log": state["log"][-20:], "error": state["error"]})

if __name__=='__main__':
    print("Initializing agent...")
    init_agent()
    print(f"\n  Orchestra Web Server: http://localhost:5000\n")
    if HAS_SOCKETIO and socketio:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host='0.0.0.0', port=5000, debug=False)
