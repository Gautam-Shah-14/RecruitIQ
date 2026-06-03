from app.core.jd_parser import parse_jd
from app.core.embedder import get_jd_embedding
from app.core.vector_store import query_candidates
from app.core.scorer import compute_skill_match, compute_seniority_fit, compute_composite_score
from app.core.reranker import rerank_candidates
import time
import uuid

def run_search_pipeline(job: dict, top_k: int, shortlist_n: int, filters: dict = None, conn=None) -> dict:
    start_time = time.time()
    
    parsed_signals = job.get("parsed_signals")
    if not parsed_signals:
        parsed_signals = parse_jd(job.get("raw_jd", ""))
        job["parsed_signals"] = parsed_signals

    jd_embedding = get_jd_embedding(job.get("title", ""), job.get("raw_jd", ""), parsed_signals)
    results = query_candidates(jd_embedding, top_k, filters)
    candidate_ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not candidate_ids:
        return {"session_id": str(uuid.uuid4()), "job_id": job.get("id"), "results": [], "processing_time_ms": int((time.time() - start_time) * 1000)}

    cursor = conn.cursor()
    format_strings = ','.join(['%s'] * len(candidate_ids))
    cursor.execute(f"SELECT * FROM candidates WHERE id IN ({format_strings})", tuple(candidate_ids))
    candidates = cursor.fetchall()
    candidates_data = {str(c["id"]): c for c in candidates}

    scored_candidates = []
    jd_skills = parsed_signals.get("required_skills", []) if parsed_signals else []
    jd_seniority = parsed_signals.get("seniority_level", "mid") if parsed_signals else "mid"

    for i, cid in enumerate(candidate_ids):
        cand = candidates_data.get(cid)
        if not cand:
            continue
        
        semantic_similarity = 1 - (distances[i] / 2)
        skill_match = compute_skill_match(jd_skills, cand.get("skills", []))
        seniority_fit = compute_seniority_fit(jd_seniority, cand.get("years_exp", 0))
        trajectory_score = cand.get("trajectory_score", 0.5)
        behavioral_score = cand.get("activity_score", 0.5)

        match_score = compute_composite_score(
            semantic_similarity, skill_match, seniority_fit, trajectory_score, behavioral_score
        )

        scored_candidates.append({
            "candidate_id": cid,
            "full_name": cand.get("full_name"),
            "headline": cand.get("headline"),
            "skills": cand.get("skills", []),
            "career_summary": cand.get("career_history", []),
            "match_score": match_score,
            "score_breakdown": {
                "semantic_similarity": semantic_similarity,
                "skill_match": skill_match,
                "seniority_fit": seniority_fit,
                "trajectory_score": trajectory_score,
                "behavioral_score": behavioral_score
            }
        })

    scored_candidates = sorted(scored_candidates, key=lambda x: x["match_score"], reverse=True)[:shortlist_n]

    candidate_summaries = []
    for c in scored_candidates:
        candidate_summaries.append({
            "candidate_id": c["candidate_id"],
            "name": c["full_name"],
            "headline": c["headline"],
            "skills": c["skills"],
            "score_breakdown": c["score_breakdown"]
        })

    reranked = rerank_candidates(job, parsed_signals, candidate_summaries)
    
    reranked_map = {r.get("candidate_id"): r for r in reranked}
    final_results = []
    
    order_ids = [r.get("candidate_id") for r in reranked] if reranked else [c["candidate_id"] for c in scored_candidates]
    
    rank = 1
    for cid in order_ids:
        cand = next((c for c in scored_candidates if c["candidate_id"] == cid), None)
        if cand:
            rerank_data = reranked_map.get(cid, {})
            final_results.append({
                "rank": rank,
                "candidate_id": cid,
                "full_name": cand["full_name"],
                "headline": cand["headline"],
                "match_score": round(cand["match_score"], 4),
                "score_breakdown": cand["score_breakdown"],
                "why_this_candidate": rerank_data.get("why_this_candidate", "Good match based on semantic and skill fit."),
                "why_not_flags": rerank_data.get("why_not_flags", [])
            })
            rank += 1

    processing_time = int((time.time() - start_time) * 1000)
    session_id = str(uuid.uuid4())

    return {
        "session_id": session_id,
        "job_id": job.get("id"),
        "results": final_results,
        "processing_time_ms": processing_time
    }
