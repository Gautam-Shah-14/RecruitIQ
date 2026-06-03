import json
from app.core.groq_client import groq_client

def parse_jd(raw_jd: str) -> dict | None:
    system = (
        "You are a technical recruiter AI. Extract structured hiring signals from job descriptions. "
        "Respond ONLY with valid JSON. No preamble, no markdown fences, no explanation."
    )
    
    user = f"""Extract the following from this job description and return as JSON:
{{
  "required_skills": [],      // hard skills, tools, languages
  "preferred_skills": [],     // nice-to-have
  "seniority_level": "",      // junior | mid | senior | staff | principal
  "years_exp_min": 0,
  "domain": [],               // primary domain tags e.g. ml, backend, devops
  "culture_signals": [],      // remote-ok, fast-paced, startup, etc
  "soft_skills": []           // communication, leadership, ownership, etc
}}

Job Description:
{raw_jd}
"""
    try:
        response_text = groq_client.chat(system, user, temperature=0.0)
        parsed = json.loads(response_text)
        return parsed
    except Exception as e:
        print(f"Error parsing JD: {e}")
        return None
