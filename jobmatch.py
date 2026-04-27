"""
tools/job_matcher.py
Embeds the user resume and job descriptions using a lightweight sentence-transformer,
then computes cosine similarity for fast, token-free matching.
No LLM tokens are consumed here — pure vector math.
"""

import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from profile_utils import load_profile


class JobMatcher:
    """
    Matches jobs to the user profile using embedding cosine similarity.
    Model: all-MiniLM-L6-v2 (~22MB, runs locally, zero API cost)
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, user_id: str = "default"):
        print(f"Loading embedding model for {user_id}...")
        self.user_id = user_id
        self.profile = load_profile(user_id)
        self.model = SentenceTransformer(self.MODEL_NAME)
        self._resume_embedding = self._build_resume_embedding()

    def _build_resume_embedding(self) -> np.ndarray:
        # Combine resume + desired titles/skills into a rich query vector
        profile_text = (
            f"{self.profile.resume_text}\n"
            f"Target roles: {', '.join(self.profile.desired_titles)}\n"
            f"Skills: {', '.join(self.profile.desired_skills)}\n"
            f"Preferred locations: {', '.join(self.profile.preferred_locations)}"
        )
        return self.model.encode(profile_text, normalize_embeddings=True)

    def score(self, job_title: str, job_description: str, company: str = "") -> float:
        """
        Returns cosine similarity [0, 1] between the resume and this job.
        Threshold in .env: MIN_MATCH_SCORE (default 0.65)
        """
        job_text = f"{job_title} at {company}\n{job_description[:1500]}"
        job_emb = self.model.encode(job_text, normalize_embeddings=True)
        score = float(np.dot(self._resume_embedding, job_emb))
        return round(max(0.0, score), 4)

    def rank(self, jobs: List[dict]) -> List[dict]:
        """Score and rank a list of job dicts (must have title, description)."""
        for j in jobs:
            j["match_score"] = self.score(
                j.get("title", ""),
                j.get("description", ""),
                j.get("company", ""),
            )
        return sorted(jobs, key=lambda x: x["match_score"], reverse=True)

    def filter_matches(self, jobs: List[dict], min_score: float = 0.65) -> List[dict]:
        ranked = self.rank(jobs)
        return [j for j in ranked if j["match_score"] >= min_score]