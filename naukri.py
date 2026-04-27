"""
portals/naukri.py
Naukri.com job scraper and apply handler.
"""

import asyncio
from typing import List
from base import BasePortalScraper, JobPosting
from profile_utils import load_profile


class NaukriScraper(BasePortalScraper):
    portal_name = "naukri"
    base_url = "https://www.naukri.com"

    async def login(self) -> bool:
        if not self.credential:
            print("⚠  No Naukri credentials stored.")
            return False
        await self._start_browser()
        try:
            await self.page.goto("https://www.naukri.com/nlogin/login", wait_until="networkidle")
            await asyncio.sleep(2)
            await self.page.fill("#usernameField", self.credential.username)
            await self.page.fill("#passwordField", self.credential.password)
            await self.page.click("button[type='submit']")
            await asyncio.sleep(3)
            print("✓ Naukri login successful")
            return True
        except Exception as e:
            print(f"✗ Naukri login failed: {e}")
            return False

    async def scrape_jobs(self, max_results: int = 50) -> List[JobPosting]:
        if not self.page:
            if not await self.login():
                return []

        jobs = []
        seen_urls = set()

        for title in self.profile.desired_titles[:2]:
            if len(jobs) >= max_results:
                break
            search_url = (
                f"https://www.naukri.com/{title.lower().replace(' ', '-')}-jobs"
                f"?experience={self.profile.experience_years}"
                f"&jobAge=1"         # posted in last 1 day
            )
            try:
                await self.page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)

                job_cards = await self.page.query_selector_all(".jobTuple")
                for card in job_cards[:25]:
                    try:
                        title_el = await card.query_selector(".title")
                        company_el = await card.query_selector(".companyInfo span.name")
                        location_el = await card.query_selector(".locWdth")
                        salary_el = await card.query_selector(".salary")
                        link_el = await card.query_selector("a.title")

                        job_link = await link_el.get_attribute("href") if link_el else ""
                        if not job_link or job_link in seen_urls:
                            continue
                        seen_urls.add(job_link)

                        job_title = (await title_el.inner_text()).strip() if title_el else title
                        company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                        location = (await location_el.inner_text()).strip() if location_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else ""

                        # Fetch description from job page
                        desc_page = await self.page.context.new_page()
                        await desc_page.goto(job_link, wait_until="domcontentloaded", timeout=15000)
                        desc_el = await desc_page.query_selector(".job-desc")
                        description = (await desc_el.inner_text())[:2000] if desc_el else ""
                        await desc_page.close()

                        jobs.append(JobPosting(
                            portal="naukri",
                            title=job_title,
                            company=company,
                            location=location,
                            url=job_link,
                            description=description,
                            salary=salary,
                        ))
                    except Exception:
                        continue
            except Exception as e:
                print(f"  Naukri scrape error: {e}")
                continue

        print(f"  Naukri: scraped {len(jobs)} jobs")
        return jobs

    async def apply_to_job(self, job: JobPosting) -> dict:
        """Apply using Naukri's quick apply feature."""
        try:
            await self.page.goto(job.url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            apply_btn = await self.page.query_selector(".apply-button button, button[id='apply-button']")
            if not apply_btn:
                return {"status": "manual_required", "notes": "No apply button"}

            import os
            if os.getenv("APPLY_DRY_RUN", "true").lower() != "false":
                return {"status": "dry_run", "notes": "DRY_RUN=true"}

            await apply_btn.click()
            await asyncio.sleep(3)

            # Handle confirmation dialog if present
            confirm = await self.page.query_selector("button[id='confirmApply']")
            if confirm:
                await confirm.click()
                await asyncio.sleep(2)

            return {"status": "applied", "notes": "Naukri quick apply submitted"}
        except Exception as e:
            return {"status": "failed", "notes": str(e)}