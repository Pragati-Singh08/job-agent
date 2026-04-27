"""
portals/linkedin.py
LinkedIn scraper + Easy Apply handler.
Uses Playwright for login and job scraping.
"""

import asyncio
from typing import List
from base import BasePortalScraper, JobPosting
from profile_utils import PROFILE


class LinkedInScraper(BasePortalScraper):
    portal_name = "linkedin"
    base_url = "https://www.linkedin.com"

    async def login(self) -> bool:
        if not self.credential:
            print("⚠  No LinkedIn credentials stored. Run: python -m tools.credential_manager")
            return False
        await self._start_browser()
        try:
            await self.page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            await self.page.fill("#username", self.credential.username)
            await self.page.fill("#password", self.credential.password)
            await self.page.click('[data-litms-control-urn="login-submit"]')
            await self.page.wait_for_url("**/feed/**", timeout=15000)
            print("✓ LinkedIn login successful")
            return True
        except Exception as e:
            print(f"✗ LinkedIn login failed: {e}")
            return False

    async def scrape_jobs(self, max_results: int = 50) -> List[JobPosting]:
        if not self.page:
            if not await self.login():
                return []

        jobs = []
        seen_urls = set()

        for title in PROFILE.desired_titles[:2]:
            for location in (["Remote"] + PROFILE.preferred_locations[:1]):
                if len(jobs) >= max_results:
                    break
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={title.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                    f"&f_TPR=r86400"   # last 24h
                    f"&f_JT=F"         # full-time
                    f"&sortBy=DD"      # date descending
                )
                try:
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2)

                    # Scroll to load more results
                    for _ in range(3):
                        await self.page.keyboard.press("End")
                        await asyncio.sleep(1)

                    cards = await self.page.query_selector_all(".job-card-container")
                    for card in cards[:25]:
                        try:
                            job_url = await card.get_attribute("data-entity-urn")
                            title_el = await card.query_selector(".job-card-list__title")
                            company_el = await card.query_selector(".job-card-container__company-name")
                            location_el = await card.query_selector(".job-card-container__metadata-item")
                            link_el = await card.query_selector("a.job-card-list__title")

                            job_link = await link_el.get_attribute("href") if link_el else ""
                            if not job_link or job_link in seen_urls:
                                continue
                            seen_urls.add(job_link)

                            full_url = f"https://www.linkedin.com{job_link}" if job_link.startswith("/") else job_link
                            job_title = (await title_el.inner_text()).strip() if title_el else title
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            loc_text = (await location_el.inner_text()).strip() if location_el else location

                            # Get job description (click card)
                            await card.click()
                            await asyncio.sleep(1.5)
                            desc_el = await self.page.query_selector(".job-view-layout .jobs-description-content")
                            description = (await desc_el.inner_text())[:2000] if desc_el else ""

                            # Check for Easy Apply
                            easy_apply_btn = await self.page.query_selector(".jobs-apply-button--top-card")
                            is_easy_apply = False
                            if easy_apply_btn:
                                btn_text = (await easy_apply_btn.inner_text()).lower()
                                is_easy_apply = "easy apply" in btn_text

                            jobs.append(JobPosting(
                                portal="linkedin",
                                title=job_title,
                                company=company,
                                location=loc_text,
                                url=full_url,
                                description=description,
                                job_type="easy_apply" if is_easy_apply else "external",
                            ))
                        except Exception:
                            continue
                except Exception as e:
                    print(f"  LinkedIn scrape error: {e}")
                    continue

        print(f"  LinkedIn: scraped {len(jobs)} jobs")
        return jobs

    async def apply_to_job(self, job: JobPosting) -> dict:
        """Submit LinkedIn Easy Apply (single-page applications only)."""
        try:
            await self.page.goto(job.url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Click Easy Apply button
            apply_btn = await self.page.query_selector(".jobs-apply-button--top-card")
            if not apply_btn:
                return {"status": "manual_required", "notes": "No Easy Apply button"}

            btn_text = (await apply_btn.inner_text()).lower()
            if "easy apply" not in btn_text:
                return {"status": "manual_required", "notes": "External application"}

            await apply_btn.click()
            await asyncio.sleep(2)

            # Fill phone if asked
            phone_field = await self.page.query_selector("input[id*='phoneNumber']")
            if phone_field:
                await phone_field.fill(PROFILE.phone)

            # Check if multi-step (skip complex flows to avoid mistakes)
            next_btn = await self.page.query_selector("button[aria-label='Continue to next step']")
            if next_btn:
                return {"status": "manual_required", "notes": "Multi-step Easy Apply – open manually"}

            # Submit
            submit_btn = await self.page.query_selector("button[aria-label*='Submit application']")
            if submit_btn:
                import os
                if os.getenv("APPLY_DRY_RUN", "true").lower() != "false":
                    return {"status": "dry_run", "notes": "DRY_RUN=true, not submitted"}
                await submit_btn.click()
                await asyncio.sleep(2)
                return {"status": "applied", "notes": "Easy Apply submitted"}

            return {"status": "manual_required", "notes": "Submit button not found"}
        except Exception as e:
            return {"status": "failed", "notes": str(e)}