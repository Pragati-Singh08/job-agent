

# """
# main.py — Job Agent (Search Mode)
# - Searches jobs from public APIs every 2 hours
# - Scores against your resume using embeddings
# - Shows everything in a web UI at http://localhost:5000
# - You apply yourself by clicking the job link

# Usage:
#   python main.py            # start web UI + background search
#   python main.py --search   # run one search cycle, no UI
#   python main.py --report   # print table in terminal
# """

# import argparse
# import asyncio
# import os
# import threading
# import time
# from datetime import datetime
# from dotenv import load_dotenv

# load_dotenv()


# def console_print(msg):
#     print(f"[{datetime.now().strftime('%H:%M')}] {msg}")


# # ── One search + match cycle ───────────────────────────────────────────────────
# def run_cycle():
#     from jobsearch import search_all_portals
#     from jobmatch import JobMatcher
#     from jobstore import JobStore

#     console_print("Searching jobs...")
#     jobs = asyncio.run(search_all_portals(limit_each=20))
#     console_print(f"Found {len(jobs)} jobs across all portals")

#     matcher = JobMatcher()
#     store   = JobStore()

#     new = 0
#     for j in jobs:
#         score = matcher.score(j.title, j.description, j.company)
#         j.match_score = score
#         _, is_new = store.upsert_job(
#             portal=j.portal, title=j.title, company=j.company,
#             location=j.location, url=j.url, description=j.description,
#             salary=j.salary, match_score=score,
#         )
#         if is_new:
#             new += 1

#     console_print(f"Saved {new} new jobs")
#     return new


# # ── Background scheduler (every 2 hours) ──────────────────────────────────────
# def start_scheduler():
#     def loop():
#         while True:
#             time.sleep(2 * 60 * 60)
#             try:
#                 run_cycle()
#             except Exception as e:
#                 console_print(f"Search error: {e}")

#     t = threading.Thread(target=loop, daemon=True)
#     t.start()
#     console_print("Scheduler started — searching every 2 hours")


# # ── Terminal report ────────────────────────────────────────────────────────────
# def show_report():
#     from jobstore import JobStore
#     from rich.table import Table
#     from rich.console import Console
#     from rich import box

#     store = JobStore()
#     stats = store.stats()
#     jobs  = store.get_all(min_score=0.0, limit=30)

#     c = Console()
#     t = Table(title="Job Matches", box=box.ROUNDED)
#     t.add_column("Title",    max_width=35, style="cyan")
#     t.add_column("Company",  max_width=22)
#     t.add_column("Portal",   style="dim")
#     t.add_column("Match",    style="green")
#     t.add_column("Location", max_width=20, style="dim")
#     t.add_column("Status",   style="yellow")
#     for j in jobs:
#         t.add_row(j["title"], j["company"] or "–", j["portal"],
#                   f"{j['match_score']:.0%}", j["location"] or "–",
#                   j["apply_status"])
#     c.print(t)
#     c.print(f"Total: {stats['total_scraped']} scraped | {stats['applied']} applied | {stats['pending']} pending")


# # ── Flask web UI ───────────────────────────────────────────────────────────────
# UI_HTML = """<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8">
# <meta name="viewport" content="width=device-width, initial-scale=1.0">
# <title>JobHunt Dashboard</title>
# <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">
# <style>
# :root{--bg:#09090f;--s1:#111118;--s2:#1a1a25;--border:rgba(255,255,255,0.07);--accent:#7c6af7;--accent2:#f0836e;--text:#e4e4f0;--muted:#5e5e75;--green:#4ade80;--amber:#fbbf24;--blue:#60a5fa}
# *{box-sizing:border-box;margin:0;padding:0}
# body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh}
# header{padding:18px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:100;gap:16px;flex-wrap:wrap}
# .logo{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;letter-spacing:-1px}.logo span{color:var(--accent)}
# .stats-row{display:flex;gap:20px;font-size:13px;color:var(--muted)}
# .stats-row b{color:var(--text);font-weight:500}
# .btn{background:var(--accent);color:#fff;border:none;padding:9px 20px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;transition:opacity .18s;white-space:nowrap}
# .btn:hover{opacity:.82}.btn:disabled{opacity:.35;cursor:not-allowed}
# .filters{padding:14px 28px;display:flex;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--border);align-items:center}
# .fi{background:var(--s1);border:1px solid var(--border);color:var(--text);padding:8px 13px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .18s}
# .fi:focus{border-color:var(--accent)}
# #si{width:220px}
# .range-wrap{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
# #sv{color:var(--accent);font-weight:500;min-width:32px}
# .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;padding:22px 28px}
# .card{background:var(--s1);border:1px solid var(--border);border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:11px;transition:border-color .18s,transform .18s;animation:fu .25s ease both}
# .card:hover{border-color:rgba(124,106,247,.4);transform:translateY(-2px)}
# .card.is-applied{opacity:.45;pointer-events:none}
# @keyframes fu{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
# .ct{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
# .ctitle{font-family:'Syne',sans-serif;font-weight:600;font-size:15px;line-height:1.35}
# .badge{font-size:11.5px;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap;flex-shrink:0}
# .bh{background:rgba(74,222,128,.13);color:var(--green)}
# .bm{background:rgba(251,191,36,.11);color:var(--amber)}
# .bl{background:rgba(255,255,255,.05);color:var(--muted)}
# .ba{background:rgba(124,106,247,.15);color:var(--accent)}
# .pills{display:flex;flex-wrap:wrap;gap:6px}
# .pill{font-size:11px;padding:3px 9px;border-radius:20px;background:var(--s2);color:var(--muted);border:1px solid var(--border)}
# .pp{color:var(--accent);border-color:rgba(124,106,247,.22);background:rgba(124,106,247,.07)}
# .pl{color:var(--blue);border-color:rgba(96,165,250,.2);background:rgba(96,165,250,.06)}
# .ps{color:var(--green);border-color:rgba(74,222,128,.2);background:rgba(74,222,128,.06)}
# .desc{font-size:12.5px;color:var(--muted);line-height:1.65;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
# .actions{display:flex;gap:8px;margin-top:2px}
# .abtn{flex:1;background:var(--accent);color:#fff;border:none;padding:9px 0;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;text-decoration:none;text-align:center;transition:opacity .18s}
# .abtn:hover{opacity:.82}
# .dbtn{background:var(--s2);color:var(--muted);border:1px solid var(--border);padding:9px 13px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;transition:all .18s}
# .dbtn:hover{background:rgba(74,222,128,.09);color:var(--green);border-color:rgba(74,222,128,.3)}
# .dbtn.done{background:rgba(74,222,128,.09);color:var(--green);border-color:rgba(74,222,128,.3);cursor:default}
# .ts{font-size:11px;color:var(--muted);text-align:right}
# .empty{grid-column:1/-1;text-align:center;padding:80px 0;color:var(--muted)}
# .empty h3{font-family:'Syne',sans-serif;font-size:20px;margin-bottom:10px;color:var(--text)}
# .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--accent);animation:p 1s infinite;margin:0 3px}
# .dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}
# @keyframes p{0%,100%{opacity:.25;transform:scale(.7)}50%{opacity:1;transform:scale(1)}}
# .toast{position:fixed;bottom:22px;right:22px;background:var(--s2);border:1px solid var(--border);color:var(--text);padding:11px 18px;border-radius:10px;font-size:13px;transform:translateY(70px);opacity:0;transition:all .28s;z-index:999}
# .toast.show{transform:translateY(0);opacity:1}
# select.fi option{background:var(--s1)}
# .last-updated{font-size:12px;color:var(--muted);align-self:center}
# .show-applied-wrap{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
# .show-applied-wrap input{accent-color:var(--accent);cursor:pointer}
# </style>
# </head>
# <body>
# <header>
#   <div class="logo">Job<span>Hunt</span></div>
#   <div class="stats-row">
#     <div>Total <b id="st">–</b></div>
#     <div>Showing <b id="ss">–</b></div>
#     <div>Applied <b id="sa">–</b></div>
#   </div>
#   <span class="last-updated" id="lu"></span>
#   <button class="btn" id="rbtn" onclick="searchNow()">Search Now</button>
# </header>

# <div class="filters">
#   <input id="si" class="fi" placeholder="Search title or company..." oninput="loadJobs()">
#   <select id="pf" class="fi" onchange="loadJobs()">
#     <option value="">All Portals</option>
#     <option>Indeed</option><option>Remotive</option><option>Arbeitnow</option>
#     <option>Himalayas</option><option>Adzuna</option><option>LinkedIn</option>
#   </select>
#   <div class="range-wrap">
#     Min match <span id="sv">0%</span>
#     <input type="range" id="sf" min="0" max="100" value="0" style="width:90px"
#       oninput="document.getElementById('sv').textContent=this.value+'%';loadJobs()">
#   </div>
#   <label class="show-applied-wrap">
#     <input type="checkbox" id="showApplied" onchange="loadJobs()"> Show applied
#   </label>
# </div>

# <div class="grid" id="grid">
#   <div class="empty"><span class="dot"></span><span class="dot"></span><span class="dot"></span><br><br>Loading jobs...</div>
# </div>
# <div class="toast" id="toast"></div>

# <script>
# function sc(s,applied){if(applied)return'ba';return s>=.7?'bh':s>=.5?'bm':'bl'}
# function ta(str){
#   if(!str)return '';
#   const d=new Date(str);
#   if(isNaN(d))return str.slice(0,10);
#   const m=Math.floor((Date.now()-d)/60000);
#   if(m<60)return m+'m ago';
#   if(m<1440)return Math.floor(m/60)+'h ago';
#   return Math.floor(m/1440)+'d ago';
# }
# function card(j){
#   const pct=(j.match_score*100).toFixed(0);
#   const applied=j.applied||j.apply_status==='applied';
#   const badgeLabel=applied?'Applied':pct+'%';
#   return `<div class="card${applied?' is-applied':''}" id="c${j.id}">
#     <div class="ct"><div class="ctitle">${j.title||'Untitled'}</div>
#     <span class="badge ${sc(j.match_score,applied)}">${badgeLabel}</span></div>
#     <div class="pills">
#       <span class="pill pp">${j.portal}</span>
#       ${j.company?`<span class="pill">${j.company}</span>`:''}
#       ${j.location?`<span class="pill pl">${j.location}</span>`:''}
#       ${j.salary?`<span class="pill ps">${j.salary}</span>`:''}
#     </div>
#     ${j.description?`<div class="desc">${j.description.replace(/</g,'&lt;')}</div>`:''}
#     <div class="actions">
#       <a class="abtn" href="${j.url}" target="_blank" rel="noopener">Apply Now →</a>
#       <button class="dbtn${applied?' done':''}" onclick="${applied?'':`done('${j.id}')`}">${applied?'✓ Applied':'✓ Mark Applied'}</button>
#     </div>
#     <div class="ts">${ta(j.scraped_at)}</div>
#   </div>`;
# }
# async function loadJobs(){
#   const p=new URLSearchParams({
#     search:document.getElementById('si').value,
#     portal:document.getElementById('pf').value,
#     min_score:document.getElementById('sf').value/100,
#     show_applied:document.getElementById('showApplied').checked?'1':'0'
#   });
#   const jobs=await fetch('/api/jobs?'+p).then(r=>r.json());
#   document.getElementById('ss').textContent=jobs.length;
#   const g=document.getElementById('grid');
#   if(!jobs.length){
#     g.innerHTML='<div class="empty"><h3>No jobs found</h3><p>Lower the match filter or click Search Now</p></div>';
#     return;
#   }
#   g.innerHTML=jobs.map(card).join('');
# }
# async function loadStats(){
#   const s=await fetch('/api/stats').then(r=>r.json());
#   document.getElementById('st').textContent=s.total_scraped;
#   document.getElementById('sa').textContent=s.applied;
#   document.getElementById('lu').textContent='Last updated '+new Date().toLocaleTimeString();
# }
# async function searchNow(){
#   const b=document.getElementById('rbtn');
#   b.disabled=true;b.textContent='Searching...';
#   await fetch('/api/search_now',{method:'POST'});
#   toast('Searching all portals — results in ~30 sec');
#   setTimeout(()=>{loadJobs();loadStats();b.disabled=false;b.textContent='Search Now';},35000);
# }
# async function done(id){
#   await fetch('/api/mark_applied/'+id,{method:'POST'});
#   const c=document.getElementById('c'+id);
#   if(c){
#     c.classList.add('is-applied');
#     const btn=c.querySelector('.dbtn');
#     if(btn){btn.textContent='✓ Applied';btn.classList.add('done');btn.onclick=null;}
#     const badge=c.querySelector('.badge');
#     if(badge){badge.className='badge ba';badge.textContent='Applied';}
#   }
#   loadStats();toast('Marked as applied!');
# }
# function toast(m){
#   const t=document.getElementById('toast');
#   t.textContent=m;t.classList.add('show');
#   setTimeout(()=>t.classList.remove('show'),3000);
# }
# setInterval(()=>{loadJobs();loadStats();},5*60*1000);
# loadJobs();loadStats();
# </script>
# </body>
# </html>"""


# def start_ui():
#     from flask import Flask, jsonify, render_template_string, request
#     from jobstore import JobStore

#     app = Flask(__name__)

#     @app.route("/")
#     def index():
#         return render_template_string(UI_HTML)

#     @app.route("/api/jobs")
#     def api_jobs():
#         store       = JobStore()
#         portal      = request.args.get("portal", "")
#         min_score   = float(request.args.get("min_score", "0.0"))
#         search      = request.args.get("search", "").lower()
#         show_applied = request.args.get("show_applied", "0") == "1"

#         jobs = store.get_all(min_score=min_score, limit=300)

#         if not show_applied:
#             jobs = [j for j in jobs if not j.get("applied")]
#         if portal:
#             jobs = [j for j in jobs if j["portal"].lower() == portal.lower()]
#         if search:
#             jobs = [j for j in jobs if search in (j["title"] or "").lower()
#                     or search in (j["company"] or "").lower()]
#         return jsonify(jobs)

#     @app.route("/api/stats")
#     def api_stats():
#         return jsonify(JobStore().stats())

#     @app.route("/api/search_now", methods=["POST"])
#     def search_now():
#         threading.Thread(target=run_cycle, daemon=True).start()
#         return jsonify({"status": "started"})

#     @app.route("/api/mark_applied/<job_id>", methods=["POST"])
#     def mark_applied(job_id):
#         JobStore().mark_applied(job_id, "applied", "Manually applied via UI")
#         return jsonify({"status": "ok"})

#     console_print("Web UI → http://localhost:5000")
#     app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# # ── Entry point ────────────────────────────────────────────────────────────────
# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--search", action="store_true", help="Run one search cycle only")
#     parser.add_argument("--report", action="store_true", help="Print terminal report")
#     args = parser.parse_args()

#     os.makedirs("data", exist_ok=True)
#     from jobstore import JobStore
#     JobStore()   # init DB

#     if args.report:
#         show_report(); return

#     if args.search:
#         run_cycle(); return

#     # Default: first search in background + scheduler + UI
#     threading.Thread(target=run_cycle, daemon=True).start()
#     start_scheduler()
#     start_ui()   # blocks (Flask)


# if __name__ == "__main__":
#     main() 

"""
main.py — Job Agent (Search Mode)
- Searches jobs from public APIs every 2 hours
- Scores against your resume using embeddings
- Shows everything in a web UI at http://localhost:5000
- Profile is editable from the UI (saved to data/profile.json)
- You apply yourself by clicking the job link

Usage:
  python main.py            # start web UI + background search
  python main.py --search   # run one search cycle, no UI
  python main.py --report   # print table in terminal
"""

import argparse
import asyncio
import os
import threading
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def console_print(msg):
    print(f"[{datetime.now().strftime('%H:%M')}] {msg}")


# ── One search + match cycle ───────────────────────────────────────────────────
def run_cycle():
    # Re-load profile fresh so latest saved values are used
    import importlib
    import profile_utils
    importlib.reload(profile_utils)

    from jobsearch import search_all_portals
    from jobmatch import JobMatcher
    from jobstore import JobStore

    profile = profile_utils.load_profile()

    if not profile.desired_titles:
        console_print("No desired titles in profile — skipping search. Fill your profile first.")
        return 0

    console_print(f"Searching jobs for: {', '.join(profile.desired_titles[:3])}...")
    jobs = asyncio.run(search_all_portals(limit_each=20))
    console_print(f"Found {len(jobs)} jobs across all portals")

    matcher = JobMatcher()
    store   = JobStore()

    new = 0
    for j in jobs:
        score = matcher.score(j.title, j.description, j.company)
        j.match_score = score
        _, is_new = store.upsert_job(
            portal=j.portal, title=j.title, company=j.company,
            location=j.location, url=j.url, description=j.description,
            salary=j.salary, match_score=score,
        )
        if is_new:
            new += 1

    console_print(f"Saved {new} new jobs")
    return new


# ── Background scheduler (every 2 hours) ──────────────────────────────────────
def start_scheduler():
    def loop():
        while True:
            time.sleep(2 * 60 * 60)
            try:
                run_cycle()
            except Exception as e:
                console_print(f"Search error: {e}")

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    console_print("Scheduler started — searching every 2 hours")


# ── Terminal report ────────────────────────────────────────────────────────────
def show_report():
    from jobstore import JobStore
    from rich.table import Table
    from rich.console import Console
    from rich import box

    store = JobStore()
    stats = store.stats()
    jobs  = store.get_all(min_score=0.0, limit=30)

    c = Console()
    t = Table(title="Job Matches", box=box.ROUNDED)
    t.add_column("Title",    max_width=35, style="cyan")
    t.add_column("Company",  max_width=22)
    t.add_column("Portal",   style="dim")
    t.add_column("Match",    style="green")
    t.add_column("Location", max_width=20, style="dim")
    t.add_column("Status",   style="yellow")
    for j in jobs:
        t.add_row(j["title"], j["company"] or "–", j["portal"],
                  f"{j['match_score']:.0%}", j["location"] or "–",
                  j["apply_status"])
    c.print(t)
    c.print(f"Total: {stats['total_scraped']} scraped | {stats['applied']} applied | {stats['pending']} pending")


# ── Flask web UI ───────────────────────────────────────────────────────────────
UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JobHunt Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
:root{--bg:#09090f;--s1:#111118;--s2:#1a1a25;--border:rgba(255,255,255,0.07);--accent:#7c6af7;--accent2:#f0836e;--text:#e4e4f0;--muted:#5e5e75;--green:#4ade80;--amber:#fbbf24;--blue:#60a5fa}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh}
header{padding:18px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:100;gap:16px;flex-wrap:wrap}
.logo{font-family:'Syne',sans-serif;font-weight:800;font-size:22px;letter-spacing:-1px}.logo span{color:var(--accent)}
.stats-row{display:flex;gap:20px;font-size:13px;color:var(--muted)}
.stats-row b{color:var(--text);font-weight:500}
.hbtns{display:flex;gap:8px}
.btn{background:var(--accent);color:#fff;border:none;padding:9px 20px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;transition:opacity .18s;white-space:nowrap}
.btn:hover{opacity:.82}.btn:disabled{opacity:.35;cursor:not-allowed}
.btn-outline{background:transparent;color:var(--text);border:1px solid var(--border);padding:9px 16px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;transition:all .18s;white-space:nowrap}
.btn-outline:hover{border-color:var(--accent);color:var(--accent)}
.filters{padding:14px 28px;display:flex;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--border);align-items:center}
.fi{background:var(--s1);border:1px solid var(--border);color:var(--text);padding:8px 13px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .18s}
.fi:focus{border-color:var(--accent)}
#si{width:220px}
.range-wrap{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
#sv{color:var(--accent);font-weight:500;min-width:32px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;padding:22px 28px}
.card{background:var(--s1);border:1px solid var(--border);border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:11px;transition:border-color .18s,transform .18s;animation:fu .25s ease both}
.card:hover{border-color:rgba(124,106,247,.4);transform:translateY(-2px)}
.card.is-applied{opacity:.45;pointer-events:none}
@keyframes fu{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.ct{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.ctitle{font-family:'Syne',sans-serif;font-weight:600;font-size:15px;line-height:1.35}
.badge{font-size:11.5px;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap;flex-shrink:0}
.bh{background:rgba(74,222,128,.13);color:var(--green)}
.bm{background:rgba(251,191,36,.11);color:var(--amber)}
.bl{background:rgba(255,255,255,.05);color:var(--muted)}
.ba{background:rgba(124,106,247,.15);color:var(--accent)}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.pill{font-size:11px;padding:3px 9px;border-radius:20px;background:var(--s2);color:var(--muted);border:1px solid var(--border)}
.pp{color:var(--accent);border-color:rgba(124,106,247,.22);background:rgba(124,106,247,.07)}
.pl{color:var(--blue);border-color:rgba(96,165,250,.2);background:rgba(96,165,250,.06)}
.ps{color:var(--green);border-color:rgba(74,222,128,.2);background:rgba(74,222,128,.06)}
.desc{font-size:12.5px;color:var(--muted);line-height:1.65;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.actions{display:flex;gap:8px;margin-top:2px}
.abtn{flex:1;background:var(--accent);color:#fff;border:none;padding:9px 0;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;text-decoration:none;text-align:center;transition:opacity .18s}
.abtn:hover{opacity:.82}
.dbtn{background:var(--s2);color:var(--muted);border:1px solid var(--border);padding:9px 13px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;cursor:pointer;transition:all .18s}
.dbtn:hover{background:rgba(74,222,128,.09);color:var(--green);border-color:rgba(74,222,128,.3)}
.dbtn.done{background:rgba(74,222,128,.09);color:var(--green);border-color:rgba(74,222,128,.3);cursor:default}
.ts{font-size:11px;color:var(--muted);text-align:right}
.empty{grid-column:1/-1;text-align:center;padding:80px 0;color:var(--muted)}
.empty h3{font-family:'Syne',sans-serif;font-size:20px;margin-bottom:10px;color:var(--text)}
.empty p{font-size:14px;margin-top:6px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--accent);animation:p 1s infinite;margin:0 3px}
.dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}
@keyframes p{0%,100%{opacity:.25;transform:scale(.7)}50%{opacity:1;transform:scale(1)}}
.toast{position:fixed;bottom:22px;right:22px;background:var(--s2);border:1px solid var(--border);color:var(--text);padding:11px 18px;border-radius:10px;font-size:13px;transform:translateY(70px);opacity:0;transition:all .28s;z-index:999}
.toast.show{transform:translateY(0);opacity:1}
select.fi option{background:var(--s1)}
.last-updated{font-size:12px;color:var(--muted);align-self:center}
.show-applied-wrap{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--muted);cursor:pointer;user-select:none}
.show-applied-wrap input{accent-color:var(--accent);cursor:pointer}
/* ── Profile Modal ─────────────────────────────────── */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;display:none;align-items:center;justify-content:center;padding:20px}
.overlay.open{display:flex}
.modal{background:var(--s1);border:1px solid var(--border);border-radius:18px;width:100%;max-width:640px;max-height:90vh;overflow-y:auto;padding:28px;display:flex;flex-direction:column;gap:20px}
.modal h2{font-family:'Syne',sans-serif;font-size:20px;font-weight:700}
.modal h2 span{color:var(--accent)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.form-grid .full{grid-column:1/-1}
.field{display:flex;flex-direction:column;gap:5px}
.field label{font-size:12px;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.field input,.field textarea{background:var(--s2);border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:9px;font-size:13px;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .18s;width:100%}
.field input:focus,.field textarea:focus{border-color:var(--accent)}
.field textarea{resize:vertical;min-height:90px}
.field .hint{font-size:11px;color:var(--muted);margin-top:2px}
.modal-actions{display:flex;gap:10px;justify-content:flex-end;padding-top:4px}
.profile-banner{background:rgba(124,106,247,.08);border:1px solid rgba(124,106,247,.2);border-radius:10px;padding:12px 16px;font-size:13px;color:var(--muted);display:flex;align-items:center;gap:10px}
.dot-green{width:8px;height:8px;border-radius:50%;background:var(--green);flex-shrink:0}
.dot-red{width:8px;height:8px;border-radius:50%;background:var(--accent2);flex-shrink:0}
</style>
</head>
<body>
<header>
  <div class="logo">Job<span>Hunt</span></div>
  <div class="stats-row">
    <div>Total <b id="st">–</b></div>
    <div>Showing <b id="ss">–</b></div>
    <div>Applied <b id="sa">–</b></div>
  </div>
  <span class="last-updated" id="lu"></span>
  <div class="hbtns">
    <button class="btn-outline" onclick="openProfile()">⚙ Profile</button>
    <button class="btn" id="rbtn" onclick="searchNow()">Search Now</button>
  </div>
</header>

<div class="filters">
  <input id="si" class="fi" placeholder="Search title or company..." oninput="loadJobs()">
  <select id="pf" class="fi" onchange="loadJobs()">
    <option value="">All Portals</option>
    <option>Indeed</option><option>Remotive</option><option>Arbeitnow</option>
    <option>Himalayas</option><option>Adzuna</option><option>LinkedIn</option>
  </select>
  <div class="range-wrap">
    Min match <span id="sv">0%</span>
    <input type="range" id="sf" min="0" max="100" value="0" style="width:90px"
      oninput="document.getElementById('sv').textContent=this.value+'%';loadJobs()">
  </div>
  <label class="show-applied-wrap">
    <input type="checkbox" id="showApplied" onchange="loadJobs()"> Show applied
  </label>
</div>

<div id="profileBanner" style="padding:10px 28px;display:none">
  <div class="profile-banner">
    <span id="bannerDot" class="dot-red"></span>
    <span id="bannerMsg">Profile not set up — click <b>⚙ Profile</b> to add your details, then hit <b>Search Now</b></span>
  </div>
</div>

<div class="grid" id="grid">
  <div class="empty"><span class="dot"></span><span class="dot"></span><span class="dot"></span><br><br>Loading jobs...</div>
</div>
<div class="toast" id="toast"></div>

<!-- Profile Modal -->
<div class="overlay" id="overlay" onclick="if(event.target===this)closeProfile()">
  <div class="modal">
    <h2>Your <span>Profile</span></h2>
    <div class="form-grid">
      <div class="field"><label>Full Name</label><input id="p_name" placeholder="Jane Doe"></div>
      <div class="field"><label>Email</label><input id="p_email" type="email" placeholder="jane@example.com"></div>
      <div class="field"><label>Phone</label><input id="p_phone" placeholder="+91-XXXXXXXXXX"></div>
      <div class="field"><label>Current Location</label><input id="p_location" placeholder="Indore, MP, India"></div>
      <div class="field"><label>LinkedIn URL</label><input id="p_linkedin" placeholder="https://linkedin.com/in/..."></div>
      <div class="field"><label>GitHub URL</label><input id="p_github" placeholder="https://github.com/..."></div>
      <div class="field full">
        <label>Desired Job Titles</label>
        <input id="p_titles" placeholder="React Developer, Frontend Engineer, MERN Stack Developer">
        <span class="hint">Comma-separated — the agent searches these exact terms</span>
      </div>
      <div class="field full">
        <label>Key Skills</label>
        <input id="p_skills" placeholder="React, TypeScript, Node.js, MongoDB, Redux">
        <span class="hint">Comma-separated — used for AI match scoring</span>
      </div>
      <div class="field">
        <label>Experience (years)</label>
        <input id="p_exp" type="number" min="0" max="40" placeholder="3">
      </div>
      <div class="field">
        <label>Preferred Locations</label>
        <input id="p_locs" placeholder="Remote, Bangalore, Pune">
        <span class="hint">Comma-separated</span>
      </div>
      <div class="field full">
        <label>Resume / Summary</label>
        <textarea id="p_resume" placeholder="Paste your resume text here. Used for AI match scoring — more detail = better matches."></textarea>
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn-outline" onclick="closeProfile()">Cancel</button>
      <button class="btn" onclick="saveProfile()">Save &amp; Close</button>
    </div>
  </div>
</div>

<script>
function sc(s,applied){if(applied)return'ba';return s>=.7?'bh':s>=.5?'bm':'bl'}
function ta(str){
  if(!str)return '';
  const d=new Date(str);
  if(isNaN(d))return str.slice(0,10);
  const m=Math.floor((Date.now()-d)/60000);
  if(m<60)return m+'m ago';if(m<1440)return Math.floor(m/60)+'h ago';
  return Math.floor(m/1440)+'d ago';
}
function card(j){
  const pct=(j.match_score*100).toFixed(0);
  const applied=j.applied||j.apply_status==='applied';
  const badgeLabel=applied?'Applied':pct+'%';
  return `<div class="card${applied?' is-applied':''}" id="c${j.id}">
    <div class="ct"><div class="ctitle">${j.title||'Untitled'}</div>
    <span class="badge ${sc(j.match_score,applied)}">${badgeLabel}</span></div>
    <div class="pills">
      <span class="pill pp">${j.portal}</span>
      ${j.company?`<span class="pill">${j.company}</span>`:''}
      ${j.location?`<span class="pill pl">${j.location}</span>`:''}
      ${j.salary?`<span class="pill ps">${j.salary}</span>`:''}
    </div>
    ${j.description?`<div class="desc">${j.description.replace(/</g,'&lt;')}</div>`:''}
    <div class="actions">
      <a class="abtn" href="${j.url}" target="_blank" rel="noopener">Apply Now →</a>
      <button class="dbtn${applied?' done':''}" onclick="${applied?'':`done('${j.id}')`}">${applied?'✓ Applied':'✓ Mark Applied'}</button>
    </div>
    <div class="ts">${ta(j.scraped_at)}</div>
  </div>`;
}
async function loadJobs(){
  const p=new URLSearchParams({
    search:document.getElementById('si').value,
    portal:document.getElementById('pf').value,
    min_score:document.getElementById('sf').value/100,
    show_applied:document.getElementById('showApplied').checked?'1':'0'
  });
  const jobs=await fetch('/api/jobs?'+p).then(r=>r.json());
  document.getElementById('ss').textContent=jobs.length;
  const g=document.getElementById('grid');
  if(!jobs.length){
    g.innerHTML='<div class="empty"><h3>No jobs found</h3><p>Lower the match filter or click Search Now</p><p style="margin-top:8px;font-size:12px">Make sure your profile has desired job titles set</p></div>';
    return;
  }
  g.innerHTML=jobs.map(card).join('');
}
async function loadStats(){
  const s=await fetch('/api/stats').then(r=>r.json());
  document.getElementById('st').textContent=s.total_scraped;
  document.getElementById('sa').textContent=s.applied;
  document.getElementById('lu').textContent='Updated '+new Date().toLocaleTimeString();
}
async function openProfile(){
  const p=await fetch('/api/profile').then(r=>r.json());
  document.getElementById('p_name').value=p.name||'';
  document.getElementById('p_email').value=p.email||'';
  document.getElementById('p_phone').value=p.phone||'';
  document.getElementById('p_location').value=p.location||'';
  document.getElementById('p_linkedin').value=p.linkedin_url||'';
  document.getElementById('p_github').value=p.github_url||'';
  document.getElementById('p_titles').value=(p.desired_titles||[]).join(', ');
  document.getElementById('p_skills').value=(p.desired_skills||[]).join(', ');
  document.getElementById('p_exp').value=p.experience_years||0;
  document.getElementById('p_locs').value=(p.preferred_locations||[]).join(', ');
  document.getElementById('p_resume').value=p.resume_text||'';
  document.getElementById('overlay').classList.add('open');
}
function closeProfile(){document.getElementById('overlay').classList.remove('open');}
async function saveProfile(){
  const csv=s=>s.split(',').map(x=>x.trim()).filter(Boolean);
  const body={
    name:document.getElementById('p_name').value.trim(),
    email:document.getElementById('p_email').value.trim(),
    phone:document.getElementById('p_phone').value.trim(),
    location:document.getElementById('p_location').value.trim(),
    linkedin_url:document.getElementById('p_linkedin').value.trim(),
    github_url:document.getElementById('p_github').value.trim(),
    desired_titles:csv(document.getElementById('p_titles').value),
    desired_skills:csv(document.getElementById('p_skills').value),
    experience_years:parseInt(document.getElementById('p_exp').value)||0,
    preferred_locations:csv(document.getElementById('p_locs').value)||['Remote'],
    resume_text:document.getElementById('p_resume').value.trim(),
    open_to_remote:true,open_to_relocation:false,
    job_types:['full-time'],avoid_companies:[],
    expected_salary_min:0,expected_salary_max:0,
  };
  const res=await fetch('/api/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(res.ok){closeProfile();toast('Profile saved! Click Search Now to find matching jobs.');updateBanner(body);}
  else toast('Failed to save profile');
}
function updateBanner(p){
  const banner=document.getElementById('profileBanner');
  const dot=document.getElementById('bannerDot');
  const msg=document.getElementById('bannerMsg');
  banner.style.display='block';
  if(!p||!(p.desired_titles||[]).length){
    dot.className='dot-red';
    msg.innerHTML='Profile not set up — click <b>⚙ Profile</b> to add your details, then hit <b>Search Now</b>';
  } else {
    dot.className='dot-green';
    msg.innerHTML=`Searching for: <b>${p.desired_titles.slice(0,3).join(', ')}</b> &nbsp;·&nbsp; Skills: <b>${(p.desired_skills||[]).slice(0,4).join(', ')||'—'}</b>`;
  }
}
async function loadBanner(){
  const p=await fetch('/api/profile').then(r=>r.json());
  updateBanner(p);
}
async function searchNow(){
  const b=document.getElementById('rbtn');
  b.disabled=true;b.textContent='Searching...';
  await fetch('/api/search_now',{method:'POST'});
  toast('Searching all portals — results in ~30 sec');
  setTimeout(()=>{loadJobs();loadStats();b.disabled=false;b.textContent='Search Now';},35000);
}
async function done(id){
  await fetch('/api/mark_applied/'+id,{method:'POST'});
  const c=document.getElementById('c'+id);
  if(c){
    c.classList.add('is-applied');
    const btn=c.querySelector('.dbtn');
    if(btn){btn.textContent='✓ Applied';btn.classList.add('done');btn.onclick=null;}
    const badge=c.querySelector('.badge');
    if(badge){badge.className='badge ba';badge.textContent='Applied';}
  }
  loadStats();toast('Marked as applied!');
}
function toast(m){
  const t=document.getElementById('toast');
  t.textContent=m;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3500);
}
setInterval(()=>{loadJobs();loadStats();},5*60*1000);
loadJobs();loadStats();loadBanner();
</script>
</body>
</html>"""


def start_ui():
    from flask import Flask, jsonify, render_template_string, request
    from jobstore import JobStore
    from profile_utils import load_profile, save_profile

    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(UI_HTML)

    @app.route("/api/jobs")
    def api_jobs():
        store        = JobStore()
        portal       = request.args.get("portal", "")
        min_score    = float(request.args.get("min_score", "0.0"))
        search       = request.args.get("search", "").lower()
        show_applied = request.args.get("show_applied", "0") == "1"

        jobs = store.get_all(min_score=min_score, limit=300)

        if not show_applied:
            jobs = [j for j in jobs if not j.get("applied")]
        if portal:
            jobs = [j for j in jobs if j["portal"].lower() == portal.lower()]
        if search:
            jobs = [j for j in jobs if search in (j["title"] or "").lower()
                    or search in (j["company"] or "").lower()]
        return jsonify(jobs)

    @app.route("/api/stats")
    def api_stats():
        return jsonify(JobStore().stats())

    @app.route("/api/profile", methods=["GET"])
    def get_profile():
        return jsonify(load_profile().model_dump())

    @app.route("/api/profile", methods=["POST"])
    def post_profile():
        data = request.get_json(force=True)
        try:
            profile = save_profile(data)
            return jsonify({"status": "ok", "profile": profile.model_dump()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/api/search_now", methods=["POST"])
    def search_now():
        threading.Thread(target=run_cycle, daemon=True).start()
        return jsonify({"status": "started"})

    @app.route("/api/mark_applied/<job_id>", methods=["POST"])
    def mark_applied(job_id):
        JobStore().mark_applied(job_id, "applied", "Manually applied via UI")
        return jsonify({"status": "ok"})

    console_print("Web UI → http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", action="store_true", help="Run one search cycle only")
    parser.add_argument("--report", action="store_true", help="Print terminal report")
    args = parser.parse_args()

    os.makedirs("data", exist_ok=True)
    from jobstore import JobStore
    JobStore()   # init DB

    if args.report:
        show_report(); return

    if args.search:
        run_cycle(); return

    # Default: first search in background + scheduler + UI
    threading.Thread(target=run_cycle, daemon=True).start()
    start_scheduler()
    start_ui()   # blocks (Flask)


if __name__ == "__main__":
    main()