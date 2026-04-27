"""
streamlit_app.py — Streamlit wrapper for JobHunt agent
Run locally:  streamlit run streamlit_app.py
"""
import streamlit as st
import asyncio
import os
import threading
from profile_utils import load_profile, save_profile
from jobstore import JobStore
from usermanager import UserManager

st.set_page_config(page_title="JobHunt", page_icon="💼", layout="wide")

os.makedirs("data", exist_ok=True)

# ── Authentication ────────────────────────────────────────────────
if "user" not in st.session_state:
    st.session_state.user = None

user_manager = UserManager()

def login_signup_page():
    st.title("💼 Welcome to JobHunt")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
            if submitted:
                success, msg = user_manager.login(username, password)
                if success:
                    st.session_state.user = username
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
                    
    with tab2:
        with st.form("signup_form"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif not new_username or not new_password:
                    st.error("Please fill all fields")
                else:
                    success, msg = user_manager.signup(new_username, new_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

def main_app():
    user_id = st.session_state.user
    
    # ── Sidebar: Profile ──────────────────────────────────────────────
    st.sidebar.title(f"👤 {user_id}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.divider()
    st.sidebar.subheader("⚙ Your Profile")
    p = load_profile(user_id)

    with st.sidebar.form("profile_form"):
        name     = st.text_input("Full Name",          value=p.name)
        email    = st.text_input("Email",              value=p.email)
        phone    = st.text_input("Phone",              value=p.phone)
        location = st.text_input("Location",           value=p.location)
        titles   = st.text_input("Desired Job Titles (comma-sep)",
                                  value=", ".join(p.desired_titles))
        skills   = st.text_input("Key Skills (comma-sep)",
                                  value=", ".join(p.desired_skills))
        exp      = st.number_input("Experience (years)", value=p.experience_years, min_value=0, max_value=40)
        locs     = st.text_input("Preferred Locations (comma-sep)",
                                  value=", ".join(p.preferred_locations))
        resume   = st.text_area("Resume / Summary", value=p.resume_text, height=180)
        saved    = st.form_submit_button("💾 Save Profile")

    if saved:
        csv = lambda s: [x.strip() for x in s.split(",") if x.strip()]
        save_profile({
            "name": name, "email": email, "phone": phone, "location": location,
            "desired_titles": csv(titles), "desired_skills": csv(skills),
            "experience_years": int(exp), "preferred_locations": csv(locs) or ["Remote"],
            "resume_text": resume,
            "open_to_remote": True, "open_to_relocation": False,
            "job_types": ["full-time"], "avoid_companies": [],
            "expected_salary_min": 0, "expected_salary_max": 0,
            "linkedin_url": "", "github_url": "", "portfolio_url": "",
        }, user_id=user_id)
        st.sidebar.success("Profile saved!")
        st.rerun()

    # ── Main area ─────────────────────────────────────────────────────
    st.title("💼 JobHunt Dashboard")

    profile = load_profile(user_id)
    if profile.desired_titles:
        st.info(f"Searching for: **{', '.join(profile.desired_titles[:3])}** · Skills: **{', '.join(profile.desired_skills[:4])}**")
    else:
        st.warning("Fill your profile in the sidebar, then click Search Now.")

    col1, col2, col3 = st.columns(3)
    store = JobStore(user_id=user_id)
    stats = store.stats()
    col1.metric("Total Scraped", stats["total_scraped"])
    col2.metric("Pending",       stats["pending"])
    col3.metric("Applied",       stats["applied"])

    if st.button("🔍 Search Now", type="primary"):
        if not profile.desired_titles:
            st.error("Add desired job titles to your profile first.")
        else:
            with st.spinner("Searching all portals..."):
                from main import run_cycle
                new = run_cycle(user_id=user_id)
                st.success(f"Found {new} new jobs!")
                st.rerun()

    # ── Filters ───────────────────────────────────────────────────────
    st.divider()
    fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 1])
    search_q    = fc1.text_input("Search title / company", placeholder="React, Bangalore...")
    portal_f    = fc2.selectbox("Portal", ["All", "Indeed", "Remotive", "Arbeitnow", "Himalayas", "Adzuna", "LinkedIn"])
    min_match   = fc3.slider("Min match %", 0, 100, 0) / 100
    show_applied = fc4.checkbox("Show applied")

    # ── Job grid ──────────────────────────────────────────────────────
    jobs = store.get_all(min_score=min_match, limit=300)
    if not show_applied:
        jobs = [j for j in jobs if not j.get("applied")]
    if portal_f != "All":
        jobs = [j for j in jobs if j["portal"].lower() == portal_f.lower()]
    if search_q:
        q = search_q.lower()
        jobs = [j for j in jobs if q in (j["title"] or "").lower() or q in (j["company"] or "").lower()]

    st.caption(f"Showing {len(jobs)} jobs")

    for j in jobs:
        pct   = int((j["match_score"] or 0) * 100)
        color = "🟢" if pct >= 70 else "🟡" if pct >= 50 else "⚪"
        badge = "✅ Applied" if j.get("applied") else f"{color} {pct}%"

        with st.expander(f"{badge}  {j['title'] or 'Untitled'}  —  {j['company'] or ''}"):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**Portal:** {j['portal']}  |  **Location:** {j['location'] or '—'}  |  **Salary:** {j['salary'] or '—'}")
            if j.get("description"):
                st.caption(j["description"][:400] + "…")
            c2.link_button("Apply Now →", j["url"] or "#")
            if not j.get("applied"):
                if c2.button("✓ Mark Applied", key=f"apply_{j['id']}"):
                    store.mark_applied(j["id"], "applied", "Marked via Streamlit UI")
                    st.rerun()

if st.session_state.user:
    main_app()
else:
    login_signup_page()