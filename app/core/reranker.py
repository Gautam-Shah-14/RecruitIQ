import json
from app.core.groq_client import groq_client

def rerank_candidates(job: dict, parsed_signals: dict, candidate_summaries: list[dict]) -> list[dict]:
    system = (
        "You are an expert technical recruiter performing a final candidate review. "
        "Re-rank the candidates for the given role based on: semantic fit, career narrative, "
        "domain depth, and culture alignment. "
        "Respond ONLY with a valid JSON array. No preamble, no markdown, no explanation."
    )
    
    user = f"""Job Title: {job.get('title', '')}
Job Summary: {job.get('raw_jd', '')}
Required Skills: {', '.join(parsed_signals.get('required_skills', []))}
Seniority: {parsed_signals.get('seniority_level', 'mid')}

Candidates (pre-scored, highest first):
{json.dumps(candidate_summaries, indent=2)}

Each candidate_summary contains: candidate_id, name, headline, skills, career_summary, score_breakdown.

Return a JSON array in your preferred order:
[
  {{
    "candidate_id": "uuid",
    "why_this_candidate": "One sentence explanation of why this candidate fits.",
    "why_not_flags": ["Any concern or gap as a short string"]
  }}
]
"""
    try:
        response_text = groq_client.chat(system, user, temperature=0.2)
        parsed = json.loads(response_text)
        return parsed
    except Exception as e:
        print(f"Error reranking candidates: {e}")
        return []
