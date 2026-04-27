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
def run_cycle(user_id="default"):
    from jobsearch import search_all_portals
    from jobmatch import JobMatcher
    from jobstore import JobStore

    console_print(f"Searching jobs for user: {user_id}...")
    jobs = asyncio.run(search_all_portals(limit_each=20, user_id=user_id))
    console_print(f"Found {len(jobs)} jobs across all portals")

    matcher = JobMatcher(user_id=user_id)
    store   = JobStore(user_id=user_id)

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

    console_print(f"Saved {new} new jobs for user: {user_id}")
    return new

# ── Background scheduler (every 2 hours) ──────────────────────────────────────
def start_scheduler(user_id="default"):
    def loop():
        while True:
            time.sleep(2 * 60 * 60)
            try:
                run_cycle(user_id=user_id)
            except Exception as e:
                console_print(f"Search error for {user_id}: {e}")

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    console_print(f"Scheduler started for {user_id} — searching every 2 hours")

# ── Terminal report ────────────────────────────────────────────────────────────
def show_report(user_id="default"):
    from jobstore import JobStore
    from rich.table import Table
    from rich.console import Console
    from rich import box

    store = JobStore(user_id=user_id)
    stats = store.stats()
    jobs  = store.get_all(min_score=0.0, limit=30)

    c = Console()
    t = Table(title=f"Job Matches for {user_id}", box=box.ROUNDED)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--user", type=str, default="default")
    args = parser.parse_args()

    if args.search:
        run_cycle(user_id=args.user)
    elif args.report:
        show_report(user_id=args.user)
    else:
        # Default behavior: run cycle once
        run_cycle(user_id=args.user)
