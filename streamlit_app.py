import streamlit as st
import requests
import json

BASE_URL = "http://localhost:8005"

st.set_page_config(page_title="RecruitIQ Tester", layout="wide")

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "user_data" not in st.session_state:
    st.session_state.user_data = None

def api_get(endpoint):
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
    return response

def api_post(endpoint, data):
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
    return response

def api_put(endpoint, data):
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    response = requests.put(f"{BASE_URL}{endpoint}", json=data, headers=headers)
    return response

# --- Sidebar Auth ---
with st.sidebar:
    st.title("🔐 Authentication")
    
    if st.session_state.token:
        st.success(f"Logged in as {st.session_state.role}")
        st.write(f"Name: {st.session_state.user_data.get('full_name', '')}")
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.role = None
            st.session_state.user_data = None
            st.rerun()
    else:
        auth_mode = st.radio("Mode", ["Login", "Register"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if auth_mode == "Register":
            role = st.selectbox("Role", ["recruiter", "candidate"])
            full_name = st.text_input("Full Name")
            
            if role == "recruiter":
                company = st.text_input("Company")
                if st.button("Register Recruiter"):
                    payload = {
                        "email": email, "password": password, "role": role, 
                        "full_name": full_name, "company": company
                    }
                    res = api_post("/auth/register", payload)
                    if res.status_code == 200:
                        st.success("Registered successfully! Please login.")
                    else:
                        st.error(f"Error: {res.text}")
                        
            else:
                headline = st.text_input("Headline")
                current_title = st.text_input("Current Title")
                current_company = st.text_input("Current Company")
                years_exp = st.number_input("Years Exp", min_value=0.0, step=0.5)
                domain_str = st.text_input("Domain (comma separated)")
                skills_str = st.text_input("Skills (comma separated)")
                
                if st.button("Register Candidate"):
                    payload = {
                        "email": email, "password": password, "role": role, 
                        "full_name": full_name, "headline": headline,
                        "current_title": current_title, "current_company": current_company,
                        "years_exp": years_exp,
                        "domain": [x.strip() for x in domain_str.split(",") if x.strip()],
                        "skills": [{"name": x.strip(), "proficiency": "intermediate", "endorsements": 0} for x in skills_str.split(",") if x.strip()],
                        "career_history": []
                    }
                    res = api_post("/auth/register", payload)
                    if res.status_code == 200:
                        st.success("Registered successfully! Please login.")
                    else:
                        st.error(f"Error: {res.text}")

        else:
            if st.button("Login"):
                res = api_post("/auth/login", {"email": email, "password": password})
                if res.status_code == 200:
                    st.session_state.token = res.json().get("access_token")
                    me_res = api_get("/auth/me")
                    if me_res.status_code == 200:
                        st.session_state.user_data = me_res.json()
                        st.session_state.role = st.session_state.user_data.get("role")
                    st.rerun()
                else:
                    st.error(f"Error: {res.text}")

# --- Main App ---
st.title("RecruitIQ - System Test Flow")

if not st.session_state.token:
    st.info("Please login or register from the sidebar to continue.")
else:
    if st.session_state.role == "candidate":
        st.header("👤 Candidate Dashboard")
        
        tab1, tab2 = st.tabs(["My Profile", "Find Matching Jobs"])
        
        with tab1:
            user = st.session_state.user_data
            
            with st.form("update_profile_form"):
                st.subheader("Update Your Information")
                
                col1, col2 = st.columns(2)
                with col1:
                    full_name = st.text_input("Full Name", value=user.get("full_name", ""))
                    current_title = st.text_input("Current Title", value=user.get("current_title", ""))
                    years_exp = st.number_input("Years Experience", value=float(user.get("years_exp", 0.0)), step=0.5)
                with col2:
                    headline = st.text_input("Headline", value=user.get("headline", ""))
                    current_company = st.text_input("Current Company", value=user.get("current_company", ""))
                
                domain_list = user.get("domain", [])
                domain_str = st.text_input("Domain (comma separated)", value=", ".join(domain_list))
                
                skills_list = user.get("skills", [])
                skills_names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills_list]
                skills_str = st.text_input("Skills (comma separated)", value=", ".join(skills_names))
                
                st.markdown("**Education (JSON Format)**")
                education_str = st.text_area("Education", value=json.dumps(user.get("education", []), indent=2), height=100)
                
                st.markdown("**Career History (JSON Format)**")
                career_str = st.text_area("Career History", value=json.dumps(user.get("career_history", []), indent=2), height=150)
                
                submitted = st.form_submit_button("Save Profile")
                
                if submitted:
                    new_skills = [{"name": x.strip(), "proficiency": "intermediate", "endorsements": 0} for x in skills_str.split(",") if x.strip()]
                    new_domain = [x.strip() for x in domain_str.split(",") if x.strip()]
                    
                    try:
                        new_education = json.loads(education_str)
                        new_career = json.loads(career_str)
                    except Exception as e:
                        st.error(f"Invalid JSON format for education or career history: {str(e)}")
                        st.stop()
                    
                    payload = {
                        "full_name": full_name,
                        "headline": headline,
                        "email": user.get("email"),
                        "location": user.get("location"),
                        "years_exp": years_exp,
                        "current_title": current_title,
                        "current_company": current_company,
                        "domain": new_domain,
                        "skills": new_skills,
                        "education": new_education,
                        "career_history": new_career,
                        "certifications": user.get("certifications", []),
                        "languages": user.get("languages", []),
                        "redrob_signals": user.get("redrob_signals", {})
                    }
                    
                    res = api_put(f"/candidates/{user.get('id')}", payload)
                    if res.status_code == 200:
                        st.success("Profile Updated Successfully!")
                        me_res = api_get("/auth/me")
                        if me_res.status_code == 200:
                            st.session_state.user_data = me_res.json()
                            st.rerun()
                    else:
                        st.error(f"Failed to update: {res.text}")
        
        with tab2:
            st.subheader("🤖 AI Job Recommendations")
            st.write("We have analyzed your profile against open roles. Here are the best fits for you:")
            
            if st.button("Generate Recommendations"):
                with st.spinner("Analyzing your profile and matching with jobs..."):
                    res = api_get("/candidates/me/recommended_jobs")
                    if res.status_code == 200:
                        recs = res.json()
                        if not recs:
                            st.info("No recommendations found at the moment.")
                        for i, rec in enumerate(recs):
                            with st.container(border=True):
                                st.subheader(f"#{i+1} - {rec.get('job_title')}")
                                st.write(f"**Match Score:** {rec.get('match_score')}%")
                                st.write(f"**Why you are a fit:** {rec.get('reason')}")
                    else:
                        st.error(f"Failed to fetch recommendations: {res.text}")
        
    elif st.session_state.role == "recruiter":
        tab1, tab2, tab3, tab4 = st.tabs(["Dashboard Stats", "Manage Jobs", "Candidate Database", "Run AI Search"])
        
        with tab1:
            st.header("📊 Dashboard Stats")
            if st.button("Refresh Stats"):
                res = api_get("/stats")
                if res.status_code == 200:
                    stats = res.json()
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Jobs", stats["total_jobs"])
                    col2.metric("Total Candidates", stats["total_candidates"])
                    col3.metric("Search Sessions", stats["total_sessions"])
                else:
                    st.error("Failed to load stats")
                    
        with tab2:
            st.header("💼 Manage Jobs")
            with st.expander("Create New Job"):
                title = st.text_input("Job Title")
                raw_jd = st.text_area("Raw Job Description", height=200)
                if st.button("Create Job"):
                    with st.spinner("Parsing JD with AI..."):
                        res = api_post("/jobs", {"title": title, "raw_jd": raw_jd})
                        if res.status_code == 201:
                            st.success("Job Created!")
                            st.json(res.json())
                        else:
                            st.error(f"Error: {res.text}")
            
            st.subheader("Your Jobs")
            if st.button("Load Jobs"):
                res = api_get("/jobs")
                if res.status_code == 200:
                    jobs = res.json()
                    for j in jobs:
                        st.write(f"**{j['title']}** (ID: `{j['id']}`)")
                        if j.get("parsed_signals"):
                            st.json(j["parsed_signals"])
                        st.divider()
                        
        with tab3:
            st.header("👥 Candidate Database")
            if st.button("Load All Candidates"):
                res = api_get("/candidates")
                if res.status_code == 200:
                    cands = res.json()
                    st.write(f"Showing {len(cands)} candidates.")
                    for c in cands[:5]: # Show first 5 for brevity
                        st.write(f"**{c.get('full_name')}** - {c.get('headline')}")
                        st.write(f"Exp: {c.get('years_exp')} | Score: {c.get('activity_score')}")
                        st.divider()
                    if len(cands) > 5:
                        st.write("...and more.")
                else:
                    st.error("Failed to load candidates")
                    
        with tab4:
            st.header("🔍 Run AI Search")
            
            res = api_get("/jobs")
            if res.status_code == 200:
                jobs = res.json()
                job_options = {f"{j['title']} (ID: {j['id']})": j["id"] for j in jobs}
                
                if job_options:
                    selected_job_label = st.selectbox("Select Job to Search For", list(job_options.keys()))
                    selected_job_id = job_options[selected_job_label]
                    
                    st.write("Filters (Optional)")
                    min_exp = st.number_input("Min Years Experience", value=0)
                    
                    if st.button("Execute Deep Search Pipeline"):
                        with st.spinner("Running Vector Retrieval -> Composite Scoring -> LLM Re-Ranking..."):
                            payload = {
                                "job_id": selected_job_id,
                                "top_k": 10,
                                "shortlist_n": 3,
                                "filters": {"min_years_exp": min_exp if min_exp > 0 else None}
                            }
                            search_res = api_post("/search", payload)
                            
                            if search_res.status_code == 200:
                                results = search_res.json()
                                st.success(f"Search Complete in {results['processing_time_ms']}ms!")
                                st.write(f"**Session ID:** `{results['session_id']}`")
                                
                                for c in results["results"]:
                                    with st.container(border=True):
                                        st.subheader(f"#{c['rank']} - {c['full_name']}")
                                        st.write(f"**Match Score:** {c['match_score']:.2f}")
                                        
                                        st.markdown(f"**Why this candidate?**\n{c['why_this_candidate']}")
                                        if c['why_not_flags']:
                                            st.markdown(f"**Flags:** {', '.join(c['why_not_flags'])}")
                                            
                                        with st.expander("View Score Breakdown"):
                                            st.json(c['score_breakdown'])
                            else:
                                st.error(f"Search Failed: {search_res.text}")
                else:
                    st.warning("Please create a job first!")
