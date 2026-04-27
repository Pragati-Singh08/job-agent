"""
portals/base.py
Abstract base class for all job portal scrapers.
Each portal implements login() and scrape_jobs().
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser
from credentialmanager import CredentialManager
from profile_utils import PROFILE


class JobPosting:
    __slots__ = ["portal", "title", "company", "location", "url",
                 "description", "salary", "job_type", "posted_date"]

    def __init__(self, portal, title, company, location, url,
                 description="", salary="", job_type="", posted_date=""):
        self.portal = portal
        self.title = title
        self.company = company
        self.location = location
        self.url = url
        self.description = description
        self.salary = salary
        self.job_type = job_type
        self.posted_date = posted_date

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


class BasePortalScraper(ABC):
    """
    Each portal scraper:
    1. Logs in with stored credentials
    2. Searches for jobs matching the profile
    3. Returns JobPosting list
    4. Optionally submits applications
    """

    portal_name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.cred_mgr = CredentialManager()
        self.credential = self.cred_mgr.get(self.portal_name)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def _start_browser(self, headless: bool = True):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self.page = await context.new_page()

    async def _close_browser(self):
        if self.browser:
            await self.browser.close()

    def _search_queries(self) -> List[str]:
        """Build search queries from the user profile."""
        return [
            f"{title} {loc}"
            for title in PROFILE.desired_titles[:3]    # limit queries
            for loc in (["Remote"] + PROFILE.preferred_locations[:2])
        ]

    @abstractmethod
    async def login(self) -> bool:
        """Log in to the portal. Return True if successful."""
        ...

    @abstractmethod
    async def scrape_jobs(self, max_results: int = 50) -> List[JobPosting]:
        """Scrape job listings. Return list of JobPosting."""
        ...

    async def apply_to_job(self, job: JobPosting) -> dict:
        """
        Override in portal subclasses that support 1-click/easy apply.
        Returns {"status": "applied"|"failed"|"manual_required", "notes": "..."}
        """
        return {"status": "manual_required", "notes": "Portal doesn't support auto-apply"}