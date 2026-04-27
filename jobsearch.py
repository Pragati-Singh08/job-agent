# """
# portals/job_search.py
# Replaces Playwright scraping with public APIs and RSS feeds.
# No login needed. No blocking. Works 100% reliably.

# Sources:
# - Indeed        → RSS feed (public, no auth)
# - LinkedIn      → RapidAPI Jobs Search (free tier: 500 req/month)
# - Remotive       → Free remote jobs JSON API
# - Adzuna         → Free API (register at developer.adzuna.com)
# - Himalayas      → Free remote jobs JSON API
# - Arbeitnow      → Free JSON API (great for India/global)
# - Cutshort       → Public RSS
# - Internshala    → RSS feed
# """

# import asyncio
# import aiohttp
# import feedparser
# import os
# from datetime import datetime, timezone
# from typing import List
# from profile_utils import PROFILE


# class JobResult:
#     __slots__ = ["portal","title","company","location","url","description","salary","posted","job_type","match_score"]
#     def __init__(self, portal, title, company, location, url,
#                  description="", salary="", posted="", job_type="", match_score=0.0):
#         self.portal=portal; self.title=title; self.company=company
#         self.location=location; self.url=url; self.description=description
#         self.salary=salary; self.posted=posted; self.job_type=job_type
#         self.match_score=match_score

#     def to_dict(self):
#         return {s: getattr(self, s) for s in self.__slots__}


# HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobAgent/1.0)"}


# # ── 1. Indeed RSS (free, no auth) ─────────────────────────────────────────────
# async def search_indeed(query: str, location: str = "India", limit: int = 20) -> List[JobResult]:
#     jobs = []
#     url = f"https://in.indeed.com/rss?q={query.replace(' ','+')}&l={location.replace(' ','+')}&sort=date&fromage=1"
#     try:
#         feed = feedparser.parse(url)
#         for entry in feed.entries[:limit]:
#             jobs.append(JobResult(
#                 portal="Indeed",
#                 title=entry.get("title",""),
#                 company=entry.get("source",{}).get("value","") if hasattr(entry.get("source",""),"get") else "",
#                 location=location,
#                 url=entry.get("link",""),
#                 description=entry.get("summary","")[:500],
#                 posted=entry.get("published",""),
#             ))
#     except Exception as e:
#         print(f"Indeed RSS error: {e}")
#     return jobs


# # ── 2. Remotive (free remote jobs JSON API) ────────────────────────────────────
# async def search_remotive(query: str, limit: int = 20) -> List[JobResult]:
#     jobs = []
#     url = f"https://remotive.com/api/remote-jobs?search={query.replace(' ','%20')}&limit={limit}"
#     try:
#         async with aiohttp.ClientSession(headers=HEADERS) as s:
#             async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
#                 data = await r.json()
#         for j in data.get("jobs", [])[:limit]:
#             jobs.append(JobResult(
#                 portal="Remotive",
#                 title=j.get("title",""),
#                 company=j.get("company_name",""),
#                 location=j.get("candidate_required_location","Remote"),
#                 url=j.get("url",""),
#                 description=j.get("description","")[:500],
#                 salary=j.get("salary",""),
#                 posted=j.get("publication_date",""),
#                 job_type=j.get("job_type",""),
#             ))
#     except Exception as e:
#         print(f"Remotive error: {e}")
#     return jobs


# # ── 3. Arbeitnow (free, India-friendly, JSON API) ──────────────────────────────
# async def search_arbeitnow(query: str, limit: int = 20) -> List[JobResult]:
#     jobs = []
#     url = f"https://www.arbeitnow.com/api/job-board-api?search={query.replace(' ','%20')}"
#     try:
#         async with aiohttp.ClientSession(headers=HEADERS) as s:
#             async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
#                 data = await r.json()
#         for j in data.get("data", [])[:limit]:
#             jobs.append(JobResult(
#                 portal="Arbeitnow",
#                 title=j.get("title",""),
#                 company=j.get("company_name",""),
#                 location=j.get("location","Remote"),
#                 url=j.get("url",""),
#                 description=j.get("description","")[:500],
#                 posted=j.get("created_at",""),
#                 job_type="remote" if j.get("remote") else "onsite",
#             ))
#     except Exception as e:
#         print(f"Arbeitnow error: {e}")
#     return jobs


# # ── 4. Himalayas (free remote jobs JSON API) ───────────────────────────────────
# async def search_himalayas(query: str, limit: int = 20) -> List[JobResult]:
#     jobs = []
#     url = f"https://himalayas.app/jobs/api?q={query.replace(' ','%20')}&limit={limit}"
#     try:
#         async with aiohttp.ClientSession(headers=HEADERS) as s:
#             async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
#                 data = await r.json()
#         for j in data.get("jobs", [])[:limit]:
#             jobs.append(JobResult(
#                 portal="Himalayas",
#                 title=j.get("title",""),
#                 company=j.get("companyName",""),
#                 location=j.get("locationRestrictions","Remote") if isinstance(j.get("locationRestrictions"),[]) else "Remote",
#                 url=j.get("applicationLink", j.get("url","")),
#                 description=j.get("description","")[:500],
#                 salary=f"{j.get('minSalary','')} - {j.get('maxSalary','')}".strip(" -"),
#                 posted=j.get("createdAt",""),
#                 job_type="remote",
#             ))
#     except Exception as e:
#         print(f"Himalayas error: {e}")
#     return jobs


# # ── 5. Adzuna (free API — register at developer.adzuna.com) ───────────────────
# async def search_adzuna(query: str, location: str = "india", limit: int = 20) -> List[JobResult]:
#     app_id  = os.getenv("ADZUNA_APP_ID","")
#     app_key = os.getenv("ADZUNA_APP_KEY","")
#     if not app_id or not app_key:
#         return []   # skip silently if not configured
#     jobs = []
#     url = (
#         f"https://api.adzuna.com/v1/api/jobs/in/search/1"
#         f"?app_id={app_id}&app_key={app_key}"
#         f"&results_per_page={limit}"
#         f"&what={query.replace(' ','%20')}"
#         f"&sort_by=date"
#         f"&max_days_old=1"
#     )
#     try:
#         async with aiohttp.ClientSession() as s:
#             async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
#                 data = await r.json()
#         for j in data.get("results", [])[:limit]:
#             jobs.append(JobResult(
#                 portal="Adzuna",
#                 title=j.get("title",""),
#                 company=j.get("company",{}).get("display_name",""),
#                 location=j.get("location",{}).get("display_name",""),
#                 url=j.get("redirect_url",""),
#                 description=j.get("description","")[:500],
#                 salary=f"₹{j.get('salary_min','')} - ₹{j.get('salary_max','')}".strip(),
#                 posted=j.get("created",""),
#             ))
#     except Exception as e:
#         print(f"Adzuna error: {e}")
#     return jobs


# # ── 6. LinkedIn Jobs via JSearch RapidAPI (optional, 500 free/month) ──────────
# async def search_linkedin_rapidapi(query: str, location: str = "India", limit: int = 10) -> List[JobResult]:
#     api_key = os.getenv("RAPIDAPI_KEY","")
#     if not api_key:
#         return []
#     jobs = []
#     url = "https://jsearch.p.rapidapi.com/search"
#     params = {"query": f"{query} in {location}", "page": "1", "num_pages": "1", "date_posted": "today"}
#     hdrs = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}
#     try:
#         async with aiohttp.ClientSession() as s:
#             async with s.get(url, headers=hdrs, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
#                 data = await r.json()
#         for j in data.get("data", [])[:limit]:
#             jobs.append(JobResult(
#                 portal="LinkedIn/Google",
#                 title=j.get("job_title",""),
#                 company=j.get("employer_name",""),
#                 location=j.get("job_city","") + ", " + j.get("job_country",""),
#                 url=j.get("job_apply_link",""),
#                 description=j.get("job_description","")[:500],
#                 salary=j.get("job_salary",""),
#                 posted=j.get("job_posted_at_datetime_utc",""),
#                 job_type=j.get("job_employment_type",""),
#             ))
#     except Exception as e:
#         print(f"JSearch error: {e}")
#     return jobs


# # ── Master search — runs all sources in parallel ───────────────────────────────
# async def search_all_portals(limit_each: int = 20) -> List[JobResult]:
#     all_jobs = []
#     queries = PROFILE.desired_titles[:3]   # use top 3 desired titles

#     tasks = []
#     for q in queries:
#         tasks += [
#             search_indeed(q, PROFILE.preferred_locations[0] if PROFILE.preferred_locations else "India", limit_each),
#             search_remotive(q, limit_each),
#             search_arbeitnow(q, limit_each),
#             search_himalayas(q, limit_each),
#             search_adzuna(q, limit="India", limit=limit_each),
#             search_linkedin_rapidapi(q, limit=10),
#         ]

#     results = await asyncio.gather(*tasks, return_exceptions=True)
#     for r in results:
#         if isinstance(r, list):
#             all_jobs.extend(r)

#     # Deduplicate by URL
#     seen = set()
#     unique = []
#     for j in all_jobs:
#         if j.url and j.url not in seen:
#             seen.add(j.url)
#             unique.append(j)

#     return unique 


"""
portals/job_search.py

Stable job search pipeline using public APIs + RSS feeds.
No login, no Playwright, no blocking.

Sources:
- Indeed (RSS)
- LinkedIn (RapidAPI JSearch)
- Remotive (API)
- Adzuna (API)
- Himalayas (API)
- Arbeitnow (API)
- Cutshort (RSS - optional)
- Internshala (RSS - optional)
"""

import asyncio
import aiohttp
import feedparser
import os
from typing import List
from profile_utils import PROFILE


# ── Job Model ────────────────────────────────────────────────────────────────
class JobResult:
    __slots__ = [
        "portal", "title", "company", "location", "url",
        "description", "salary", "posted", "job_type", "match_score"
    ]

    def __init__(
        self,
        portal,
        title,
        company,
        location,
        url,
        description="",
        salary="",
        posted="",
        job_type="",
        match_score=0.0,
    ):
        self.portal = portal
        self.title = title
        self.company = company
        self.location = location
        self.url = url
        self.description = description
        self.salary = salary
        self.posted = posted
        self.job_type = job_type
        self.match_score = match_score

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


HEADERS = {"User-Agent": "JobAgent/1.0"}


# ── 1. Indeed RSS ────────────────────────────────────────────────────────────
async def search_indeed(query: str, location: str = "India", limit: int = 20):
    jobs = []
    url = f"https://in.indeed.com/rss?q={query.replace(' ','+')}&l={location.replace(' ','+')}"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            jobs.append(JobResult(
                portal="Indeed",
                title=entry.get("title", ""),
                company="",
                location=location,
                url=entry.get("link", ""),
                description=entry.get("summary", "")[:500],
                posted=entry.get("published", ""),
            ))
    except Exception as e:
        print(f"Indeed error: {e}")
    return jobs


# ── 2. Remotive ──────────────────────────────────────────────────────────────
async def search_remotive(query: str, limit: int = 20):
    url = f"https://remotive.com/api/remote-jobs?search={query}&limit={limit}"
    jobs = []

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(url) as r:
                data = await r.json()

        for j in data.get("jobs", [])[:limit]:
            jobs.append(JobResult(
                portal="Remotive",
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                location=j.get("candidate_required_location", "Remote"),
                url=j.get("url", ""),
                description=j.get("description", "")[:500],
                posted=j.get("publication_date", ""),
            ))
    except Exception as e:
        print(f"Remotive error: {e}")

    return jobs


# ── 3. Arbeitnow ─────────────────────────────────────────────────────────────
async def search_arbeitnow(query: str, limit: int = 20):
    url = f"https://www.arbeitnow.com/api/job-board-api?search={query}"
    jobs = []

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(url) as r:
                data = await r.json()

        for j in data.get("data", [])[:limit]:
            jobs.append(JobResult(
                portal="Arbeitnow",
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                location=j.get("location", "Remote"),
                url=j.get("url", ""),
                description=j.get("description", "")[:500],
                posted=j.get("created_at", ""),
            ))
    except Exception as e:
        print(f"Arbeitnow error: {e}")

    return jobs


# ── 4. Himalayas ─────────────────────────────────────────────────────────────
async def search_himalayas(query: str, limit: int = 20):
    url = f"https://himalayas.app/jobs/api?q={query}&limit={limit}"
    jobs = []

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(url) as r:
                data = await r.json()

        for j in data.get("jobs", [])[:limit]:

            location = (
                "Remote"
                if isinstance(j.get("locationRestrictions"), list)
                else j.get("locationRestrictions", "Remote")
            )

            jobs.append(JobResult(
                portal="Himalayas",
                title=j.get("title", ""),
                company=j.get("companyName", ""),
                location=location,
                url=j.get("applicationLink", ""),
                description=j.get("description", "")[:500],
                posted=j.get("createdAt", ""),
            ))
    except Exception as e:
        print(f"Himalayas error: {e}")

    return jobs


# ── 5. Adzuna API ────────────────────────────────────────────────────────────
async def search_adzuna(query: str, location: str = "India", limit: int = 20):
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")

    if not app_id or not app_key:
        return []

    url = (
        f"https://api.adzuna.com/v1/api/jobs/in/search/1"
        f"?app_id={app_id}&app_key={app_key}"
        f"&what={query}"
        f"&results_per_page={limit}"
    )

    jobs = []

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                data = await r.json()

        for j in data.get("results", [])[:limit]:
            jobs.append(JobResult(
                portal="Adzuna",
                title=j.get("title", ""),
                company=j.get("company", {}).get("display_name", ""),
                location=j.get("location", {}).get("display_name", ""),
                url=j.get("redirect_url", ""),
                description=j.get("description", "")[:500],
                posted=j.get("created", ""),
            ))
    except Exception as e:
        print(f"Adzuna error: {e}")

    return jobs


# ── 6. LinkedIn via RapidAPI ────────────────────────────────────────────────
async def search_linkedin_rapidapi(query: str, location: str = "India", limit: int = 10):
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        return []

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    params = {
        "query": f"{query} in {location}",
        "page": "1",
        "num_pages": "1",
    }

    jobs = []

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, params=params) as r:
                data = await r.json()

        for j in data.get("data", [])[:limit]:
            jobs.append(JobResult(
                portal="LinkedIn",
                title=j.get("job_title", ""),
                company=j.get("employer_name", ""),
                location=f"{j.get('job_city','')}, {j.get('job_country','')}",
                url=j.get("job_apply_link", ""),
                description=j.get("job_description", "")[:500],
                posted=j.get("job_posted_at_datetime_utc", ""),
            ))
    except Exception as e:
        print(f"RapidAPI error: {e}")

    return jobs


# ── MASTER PIPELINE ──────────────────────────────────────────────────────────
async def search_all_portals(limit_each: int = 20):
    all_jobs = []

    queries = PROFILE.desired_titles[:3]
    location = PROFILE.preferred_locations[0] if PROFILE.preferred_locations else "India"

    tasks = []

    for q in queries:
        tasks += [
            search_indeed(q, location, limit_each),
            search_remotive(q, limit_each),
            search_arbeitnow(q, limit_each),
            search_himalayas(q, limit_each),
            search_adzuna(q, location, limit_each),
            search_linkedin_rapidapi(q, location, 10),
        ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    jobs = []
    for r in results:
        if isinstance(r, list):
            jobs.extend(r)

    # Deduplicate
    seen = set()
    unique = []

    for j in jobs:
        if j.url and j.url not in seen:
            seen.add(j.url)
            unique.append(j)

    return unique