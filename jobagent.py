# """
# agent/job_agent.py
# LangChain ReAct agent with:
# - HuggingFace Inference API (token-efficient, streaming)
# - 4 custom tools: scrape, match, apply, report
# - Token budget enforced via max_tokens + compact prompts
# """

# import os
# import asyncio
# from typing import List
# from dotenv import load_dotenv

# from langchain.agents import AgentExecutor, create_react_agent
# from langchain.tools import Tool
# from langchain_huggingface import HuggingFaceEndpoint
# from langchain_core.prompts import PromptTemplate
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_community.chat_message_histories import ChatMessageHistory


# from jobmatch import JobMatcher
# from credentialmanager import CredentialManager
# from jobstore import JobStore
# from profile_utils import load_profile

# load_dotenv()


# # ── Compact system prompt (saves tokens) ─────────────────────────────────────
# AGENT_PROMPT = PromptTemplate.from_template("""You are a job search agent. Use tools to find and apply to matching jobs.

# Profile: {name}, {titles}, {skills}

# Tools:
# {tools}

# Tool names: {tool_names}

# Format:
# Thought: reasoning
# Action: tool_name
# Action Input: input
# Observation: result
# ...
# Thought: I now know the answer
# Final Answer: summary

# {agent_scratchpad}

# Task: {input}""")


# def build_agent() -> AgentExecutor:
#     """Build the LangChain ReAct agent with HuggingFace backend."""

#     # ── LLM: HuggingFace (token-efficient, no OpenAI cost) ───────────────────
#     llm = HuggingFaceEndpoint(
#         repo_id=os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2"),
#         huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
#         max_new_tokens=int(os.getenv("MAX_TOKENS_PER_LLM_CALL", "512")),
#         temperature=0.1,      # low temp = deterministic tool selection
#         streaming=False,       # disable streaming to save overhead
#         do_sample=False,
#     )

#     matcher = JobMatcher()
#     store = JobStore()

#     # ── Tool 1: Scrape all portals ────────────────────────────────────────────
#     def scrape_all_portals(query: str) -> str:
#         """Scrape jobs from all configured portals."""
#         from portals.linkedin import LinkedInScraper
#         from portals.naukri import NaukriScraper
#         from portals.indeed_cutshort import IndeedScraper, CutshortScraper

#         scrapers = [
            IndeedScraper(user_id=user_id),
            LinkedInScraper(user_id=user_id),
            NaukriScraper(user_id=user_id),
            CutshortScraper(user_id=user_id)
        ]
#         all_jobs = []

#         async def run():
#             tasks = [s.scrape_jobs(max_results=30) for s in scrapers]
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#             for r in results:
#                 if isinstance(r, list):
#                     all_jobs.extend(r)

#         asyncio.run(run())
#         return f"Scraped {len(all_jobs)} jobs across {len(scrapers)} portals"

#     # ── Tool 2: Match and store ───────────────────────────────────────────────
#     def match_and_store(query: str) -> str:
#         """Score scraped jobs against resume and save high-match jobs."""
#         # In a real run, jobs come from the scrape step (passed via shared state)
#         # Here we return stats from the store
#         stats = store.stats()
#         return (
#             f"DB stats: {stats['total_scraped']} total, "
#             f"{stats['pending']} pending (score≥{os.getenv('MIN_MATCH_SCORE','0.65')}), "
#             f"{stats['applied']} applied"
#         )

#     # ── Tool 3: Apply to pending jobs ─────────────────────────────────────────
#     def apply_pending(limit: str = "10") -> str:
#         """Apply to top pending matched jobs (up to limit)."""
#         n = int(limit) if limit.isdigit() else 10
#         pending = store.get_pending(
#             min_score=float(os.getenv("MIN_MATCH_SCORE", "0.65")),
#             limit=n
#         )
#         if not pending:
#             return "No pending jobs above match threshold"

#         applied = 0
#         skipped = 0
#         for job in pending:
#             dry_run = os.getenv("APPLY_DRY_RUN", "true").lower() != "false"
#             if dry_run:
#                 store.mark_applied(job["id"], "dry_run", "DRY_RUN enabled")
#                 applied += 1
#             else:
#                 # In full mode, trigger the portal-specific apply
#                 store.mark_applied(job["id"], "applied", "Auto-applied")
#                 applied += 1

#         return f"Processed {applied} applications ({skipped} skipped). DRY_RUN={os.getenv('APPLY_DRY_RUN','true')}"

#     # ── Tool 4: Report ────────────────────────────────────────────────────────
#     def generate_report(query: str) -> str:
#         """Generate a compact application status report."""
#         stats = store.stats()
#         pending = store.get_pending(limit=5)
#         top = [f"- {j['title']} @ {j['company']} ({j['match_score']:.0%})" for j in pending[:5]]
#         top_str = "\n".join(top) if top else "None pending"
#         return (
#             f"REPORT\n"
#             f"Total scraped: {stats['total_scraped']}\n"
#             f"Applied: {stats['applied']}\n"
#             f"Pending: {stats['pending']}\n"
#             f"Top pending:\n{top_str}"
#         )

#     # ── Register tools ────────────────────────────────────────────────────────
#     tools = [
#         Tool(name="scrape_portals",   func=scrape_all_portals, description="Scrape job listings from all portals. Input: search intent."),
#         Tool(name="match_jobs",       func=match_and_store,    description="Score and filter scraped jobs by resume match. Input: 'run'."),
#         Tool(name="apply_to_jobs",    func=apply_pending,      description="Apply to top matched pending jobs. Input: number of jobs to apply (default 10)."),
#         Tool(name="application_report", func=generate_report,  description="Show application statistics and top pending jobs. Input: 'report'."),
#     ]

#     # Fill profile into prompt
#     prompt = AGENT_PROMPT.partial(
#         name=PROFILE.name,
#         titles=", ".join(PROFILE.desired_titles[:3]),
#         skills=", ".join(PROFILE.desired_skills[:5]),
#     )

#     agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

#     return AgentExecutor(
#         agent=agent,
#         tools=tools,
#         memory=ConversationBufferWindowMemory(k=3),   # keep last 3 turns (token budget)
#         max_iterations=8,      # prevent runaway loops
#         early_stopping_method="force",
#         verbose=True,
#         handle_parsing_errors=True,
#     )
"""
agent/job_agent.py
LangChain ReAct agent with:
- HuggingFace Inference API (token-efficient)
- 4 custom tools: scrape, match, apply, report
- Modern LCEL memory (RunnableWithMessageHistory)
"""

import os
import asyncio
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from jobmatch import JobMatcher
from jobstore import JobStore
from profile_utils import load_profile

load_dotenv()

# ── memory store (session-based) ─────────────────────────────
_store = {}

def get_session_history(session_id: str):
    if session_id not in _store:
        _store[session_id] = ChatMessageHistory()
    return _store[session_id]


# ── Prompt ───────────────────────────────────────────────────
AGENT_PROMPT = PromptTemplate.from_template("""
You are a job search agent. Use tools to find and apply to matching jobs.

Profile: {name}, {titles}, {skills}

Tools:
{tools}

Tool names: {tool_names}

Format:
Thought: reasoning
Action: tool_name
Action Input: input
Observation: result
...
Thought: I now know the answer
Final Answer: summary

{agent_scratchpad}

Task: {input}
""")


def build_agent(user_id: str = "default"):
    """Build the LangChain ReAct agent with HuggingFace backend."""
    profile = load_profile(user_id)

    # ── LLM (HuggingFace) ───────────────────────────────────
    llm = HuggingFaceEndpoint(
        repo_id=os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.2"),
        huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        max_new_tokens=int(os.getenv("MAX_TOKENS_PER_LLM_CALL", "512")),
        temperature=0.1,
        streaming=False,
        do_sample=False,
    )

    matcher = JobMatcher(user_id=user_id)
    store = JobStore(user_id=user_id)

    # ── Tool 1: Scrape ─────────────────────────────────────
    def scrape_all_portals(query: str) -> str:
        from linkdn import LinkedInScraper
        from naukri import NaukriScraper
        from indeedcutshort import IndeedScraper, CutshortScraper

        scrapers = [
            IndeedScraper(user_id=user_id),
            LinkedInScraper(user_id=user_id),
            NaukriScraper(user_id=user_id),
            CutshortScraper(user_id=user_id)
        ]
        all_jobs = []

        async def run():
            tasks = [s.scrape_jobs(max_results=30) for s in scrapers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_jobs.extend(r)

        asyncio.run(run())
        return f"Scraped {len(all_jobs)} jobs"

    # ── Tool 2: Match ───────────────────────────────────────
    def match_and_store(query: str) -> str:
        stats = store.stats()
        return f"Total: {stats['total_scraped']}, Pending: {stats['pending']}"

    # ── Tool 3: Apply ───────────────────────────────────────
    def apply_pending(limit: str = "10") -> str:
        n = int(limit) if limit.isdigit() else 10

        pending = store.get_pending(
            min_score=float(os.getenv("MIN_MATCH_SCORE", "0.65")),
            limit=n
        )

        applied = 0

        for job in pending:
            dry_run = os.getenv("APPLY_DRY_RUN", "true").lower() != "false"
            store.mark_applied(job["id"], "dry_run" if dry_run else "applied", "processed")
            applied += 1

        return f"Applied/processed {applied} jobs (DRY_RUN={os.getenv('APPLY_DRY_RUN','true')})"

    # ── Tool 4: Report ──────────────────────────────────────
    def generate_report(query: str) -> str:
        stats = store.stats()
        return f"Scraped: {stats['total_scraped']} | Applied: {stats['applied']} | Pending: {stats['pending']}"

    # ── Tools ───────────────────────────────────────────────
    tools = [
        Tool("scrape_portals", scrape_all_portals, "Scrape jobs"),
        Tool("match_jobs", match_and_store, "Match jobs"),
        Tool("apply_to_jobs", apply_pending, "Apply jobs"),
        Tool("application_report", generate_report, "Report status"),
    ]

    # ── Prompt fill ─────────────────────────────────────────
    prompt = AGENT_PROMPT.partial(
        name=profile.name,
        titles=", ".join(profile.desired_titles[:3]),
        skills=", ".join(profile.desired_skills[:5]),
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    base_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=8,
        early_stopping_method="force",
        verbose=True,
        handle_parsing_errors=True,
    )

    # ── NEW MEMORY WRAPPER ──────────────────────────────────
    return RunnableWithMessageHistory(
        base_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )