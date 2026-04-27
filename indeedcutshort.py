"""
portals/indeed.py + portals/cutshort.py
Indeed uses BeautifulSoup (no login needed for scraping public results).
Cutshort uses Playwright with credential login.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List
from base import BasePortalScraper, JobPosting
from profile_utils import load_profile


# ──────────────────────────────────────────────────────────
#  Indeed (public search – no login required for scraping)
# ──────────────────────────────────────────────────────────

class IndeedScraper(BasePortalScraper):
    portal_name = "indeed"
    base_url = "https://in.indeed.com"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    async def login(self) -> bool:
        # Indeed public search doesn't need login
        return True

    async def scrape_jobs(self, max_results: int = 50) -> List[JobPosting]:
        jobs = []
        seen = set()

        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            for title in self.profile.desired_titles[:2]:
                for loc in (["Remote"] + self.profile.preferred_locations[:1]):
                    if len(jobs) >= max_results:
                        break
                    url = (
                        f"https://in.indeed.com/jobs"
                        f"?q={title.replace(' ', '+')}"
                        f"&l={loc.replace(' ', '+')}"
                        f"&fromage=1"    # last 1 day
                        f"&sort=date"
                    )
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            html = await resp.text()
                        soup = BeautifulSoup(html, "lxml")
                        cards = soup.select(".job_seen_beacon, .tapItem")

                        for card in cards[:20]:
                            try:
                                title_el = card.select_one("h2.jobTitle a, .jobTitle span")
                                company_el = card.select_one(".companyName")
                                location_el = card.select_one(".companyLocation")
                                salary_el = card.select_one(".salary-snippet")
                                link_el = card.select_one("h2.jobTitle a")

                                href = link_el.get("href", "") if link_el else ""
                                if not href or href in seen:
                                    continue
                                seen.add(href)

                                full_url = f"https://in.indeed.com{href}" if href.startswith("/") else href
                                jobs.append(JobPosting(
                                    portal="indeed",
                                    title=title_el.get_text(strip=True) if title_el else title,
                                    company=company_el.get_text(strip=True) if company_el else "",
                                    location=location_el.get_text(strip=True) if location_el else loc,
                                    url=full_url,
                                    description="",   # fetch on demand during matching
                                    salary=salary_el.get_text(strip=True) if salary_el else "",
                                ))
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"  Indeed scrape error: {e}")

        print(f"  Indeed: scraped {len(jobs)} jobs")
        return jobs

    async def apply_to_job(self, job: JobPosting) -> dict:
        return {"status": "manual_required", "notes": "Indeed apply requires account login – open link manually"}


# ──────────────────────────────────────────────────────────
#  Cutshort
# ──────────────────────────────────────────────────────────

class CutshortScraper(BasePortalScraper):
    portal_name = "cutshort"
    base_url = "https://cutshort.io"

    async def login(self) -> bool:
        if not self.credential:
            print("⚠  No Cutshort credentials stored.")
            return False
        await self._start_browser()
        try:
            await self.page.goto("https://cutshort.io/login", wait_until="networkidle")
            await asyncio.sleep(1)
            await self.page.fill("input[name='email'], input[type='email']", self.credential.username)
            await self.page.fill("input[name='password'], input[type='password']", self.credential.password)
            await self.page.click("button[type='submit']")
            await asyncio.sleep(3)
            print("✓ Cutshort login successful")
            return True
        except Exception as e:
            print(f"✗ Cutshort login failed: {e}")
            return False

    async def scrape_jobs(self, max_results: int = 30) -> List[JobPosting]:
        if not self.page:
            if not await self.login():
                return []

        jobs = []
        try:
            for title in self.profile.desired_titles[:2]:
                url = f"https://cutshort.io/jobs?query={title.replace(' ', '%20')}&sort=recent"
                await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)

                cards = await self.page.query_selector_all(".job-card, [data-testid='job-card']")
                for card in cards[:15]:
                    try:
                        title_el = await card.query_selector("h3, .job-title")
                        company_el = await card.query_selector(".company-name")
                        location_el = await card.query_selector(".location")
                        link_el = await card.query_selector("a")

                        href = await link_el.get_attribute("href") if link_el else ""
                        full_url = f"https://cutshort.io{href}" if href.startswith("/") else href

                        jobs.append(JobPosting(
                            portal="cutshort",
                            title=(await title_el.inner_text()).strip() if title_el else title,
                            company=(await company_el.inner_text()).strip() if company_el else "",
                            location=(await location_el.inner_text()).strip() if location_el else "",
                            url=full_url,
                            description="",
                        ))
                    except Exception:
                        continue
        except Exception as e:
            print(f"  Cutshort scrape error: {e}")

        print(f"  Cutshort: scraped {len(jobs)} jobs")
        return jobs

    async def apply_to_job(self, job: JobPosting) -> dict:
        try:
            await self.page.goto(job.url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            btn = await self.page.query_selector("button.apply-btn, [data-testid='apply-button']")
            if not btn:
                return {"status": "manual_required", "notes": "No apply button found"}
            import os
            if os.getenv("APPLY_DRY_RUN", "true").lower() != "false":
                return {"status": "dry_run", "notes": "DRY_RUN=true"}
            await btn.click()
            await asyncio.sleep(2)
            return {"status": "applied", "notes": "Cutshort applied"}
        except Exception as e:
            return {"status": "failed", "notes": str(e)}