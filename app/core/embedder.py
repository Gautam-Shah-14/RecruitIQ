from sentence_transformers import SentenceTransformer

# Load model locally
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_jd_embedding(title: str, raw_jd: str, parsed_signals: dict = None) -> list[float]:
    jd_text = f"{title}. {raw_jd}"
    if parsed_signals and "required_skills" in parsed_signals:
        jd_text += f" Required skills: {', '.join(parsed_signals['required_skills'])}"
    return model.encode([jd_text])[0].tolist()

def get_candidate_embedding(candidate) -> list[float]:
    # candidate can be dict or object
    if isinstance(candidate, dict):
        text  = f"{candidate.get('current_title', '')} at {candidate.get('current_company', '')}. "
        
        skills = candidate.get('skills', [])
        skill_names = [s.get('name', '') if isinstance(s, dict) else str(s) for s in skills]
        text += f"Skills: {', '.join(skill_names)}. "
        
        text += f"Domain: {', '.join(candidate.get('domain', []))}. "
        text += f"{candidate.get('years_exp', 0)} years of experience. "
        for role in candidate.get('career_history', [])[-2:]:
            desc = role.get('description', role.get('desc', ''))
            text += f"{role.get('title', '')} at {role.get('company', '')}: {desc}. "
    else:
        text  = f"{candidate.current_title} at {candidate.current_company}. "
        
        skill_names = [s.get('name', '') if isinstance(s, dict) else str(s) for s in candidate.skills]
        text += f"Skills: {', '.join(skill_names)}. "
        
        text += f"Domain: {', '.join(candidate.domain)}. "
        text += f"{candidate.years_exp} years of experience. "
        for role in candidate.career_history[-2:]:
            desc = getattr(role, 'description', getattr(role, 'desc', ''))
            text += f"{role.title} at {role.company}: {desc}. "
    return model.encode([text])[0].tolist()
