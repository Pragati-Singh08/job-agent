# """
# config/profile.py – Your job-seeker profile.
# Fill this in once; the agent uses it for matching and cover letters.
# """

# from pydantic import BaseModel
# from typing import List, Optional


# class JobSeekerProfile(BaseModel):
#     # ── Personal ─────────────────────────────────────────
#     name: str = "pragati"
#     email: str = "connecttopragati@08"
#     phone: str = "+91-XXXXXXXXXX"
#     location: str = "Indore, Madhya Pradesh, India"
#     linkedin_url: str = ""
#     github_url: str = ""
#     portfolio_url: str = ""

#     # ── Resume text (paste your resume here) ─────────────
#     resume_text: str = """
#     YOUR RESUME TEXT HERE
#     Include: work experience, skills, education, projects.
#     The agent embeds this for semantic job matching.
#     """

#     # ── Target roles ─────────────────────────────────────
#     desired_titles: List[str] = [
#         "Software Engineer",
#         "Backend Developer",
#         "Python Developer",
#         "Full Stack Developer",
#     ]
#     desired_skills: List[str] = [
#         "Python",  "React", "Node.js",
#         "SQL" ,"NOSQL" ,"Docker", "AWS","GEN AI","LLMs Integration","Microservices","Agile Methodologies","CI/CD", "Git", "Unit Testing","Typescript","Kubernetes","javascript","GraphQL","Rest apis","Cloud Computing","Data Structures","Algorithms"
#     ]
#     experience_years: int = 2
#     expected_salary_min: int = 600000   # INR per year
#     expected_salary_max: int = 1500000

#     # ── Location preferences ──────────────────────────────
#     preferred_locations: List[str] = ["Remote", "Bangalore", "Pune", "Hyderabad", "Indore"]
#     open_to_remote: bool = True
#     open_to_relocation: bool = True

#     # ── Job type ──────────────────────────────────────────
#     job_types: List[str] = ["full-time"]   # full-time, contract, internship
#     avoid_companies: List[str] = []        # blacklist


# # Singleton profile – import and edit this
# PROFILE = JobSeekerProfile() 

"""
config/profile_utils.py
Loads job-seeker profile from profile.json (data/profile.json).
Falls back to defaults if file missing.
The agent, matcher, and scrapers all import PROFILE from here.
"""

import json
import os
from pydantic import BaseModel
from typing import List

PROFILE_DIR = os.getenv("PROFILE_DIR", "./data/profiles")

def get_profile_path(user_id: str = "default") -> str:
    return os.path.join(PROFILE_DIR, f"profile_{user_id}.json")


class JobSeekerProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    resume_text: str = ""
    desired_titles: List[str] = []
    desired_skills: List[str] = []
    experience_years: int = 0
    expected_salary_min: int = 0
    expected_salary_max: int = 0
    preferred_locations: List[str] = ["Remote"]
    open_to_remote: bool = True
    open_to_relocation: bool = False
    job_types: List[str] = ["full-time"]
    avoid_companies: List[str] = []


def load_profile(user_id: str = "default") -> JobSeekerProfile:
    path = get_profile_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return JobSeekerProfile(**data)
        except Exception as e:
            print(f"[profile] Failed to load {path}: {e}")
    return JobSeekerProfile()


def save_profile(data: dict, user_id: str = "default"):
    path = get_profile_path(user_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Validate via pydantic before saving
    profile = JobSeekerProfile(**data)
    with open(path, "w") as f:
        json.dump(profile.model_dump(), f, indent=2)
    return profile


# Profile storage directory