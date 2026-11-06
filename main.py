from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import uvicorn

from modules.parser.cv_parser import CVParser
from modules.parser.job_offer_parser import JobOfferParser
from modules.rag.retriever import RAGRetriever
from modules.rag.knowledge_base import knowledge_documents
from modules.agents.final_scorer import FinalScorer
from modules.agents.hr_preference_learner import get_hr_learner
from modules.storage.score_store import get_score_store
from modules.auth.jwt_guard import require_auth, require_role
from rabbitmq_consumer import start_consumer

app = FastAPI(
    title="ATS Service",
    description="Service de scoring automatique des CVs avec apprentissage RH",
    version="2.0.0"
)

# Origines autorisées (séparées par des virgules). Le frontend passe par la gateway Nginx
# (même origine), donc on n'ouvre pas le service à tous les sites.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost,http://localhost:4200").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modules ───────────────────────────────────────────────────────────────────
parser      = CVParser()
job_parser  = JobOfferParser()
scorer      = FinalScorer()
store       = get_score_store()
hr_learner  = get_hr_learner()
retriever   = RAGRetriever()
if not retriever.is_indexed():
    retriever.index_knowledge_base(knowledge_documents)

# ── Modèles ───────────────────────────────────────────────────────────────────
class JobOffer(BaseModel):
    job_offer_id: str
    title: str
    description: str
    required_skills: list[str]
    required_experience: int
    required_education: str
    soft_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    domain: str = ""
    seniority: str = ""

class ScoreRequest(BaseModel):
    candidate_id: str
    job_offer_id: str
    cv_text: str
    job_offer: JobOffer

class ScoreResponse(BaseModel):
    candidate_id: str
    job_offer_id: str
    final_score: float
    original_score: Optional[float] = None
    grade: str
    recommendation: str
    breakdown: dict
    explanation: dict
    hr_adjusted: bool = False
    weights_applied: Optional[dict] = None

class JobOfferTextRequest(BaseModel):
    job_offer_id: str
    raw_text: str

class HRFeedbackRequest(BaseModel):
    job_offer_id: str
    chosen_candidate_id: str
    rejected_candidate_ids: list[str] = []
    reason: Optional[str] = None

class BulkScoreRequest(BaseModel):
    job_offer_id: str
    candidates: list[dict]
    job_offer: JobOffer

# ── Endpoints publics (pas de token) ─────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "ATS Service", "status": "running ✅", "version": "2.0.0",
            "auth": "JWT Bearer requis sur tous les endpoints /api/ats/*"}

@app.get("/health")
def health():
    return {"status": "ok",
            "total_scores": sum(len(store._data.get(k, [])) for k in store._data),
            "hr_weights": hr_learner.get_weights()}

# ── Parsing (tout utilisateur authentifié) ────────────────────────────────────

@app.post("/api/ats/parse-cv")
async def parse_cv(file: UploadFile = File(...), _u: dict = Depends(require_auth)):
    file_bytes = await file.read()
    text = parser.parse(file_bytes, file.filename)
    return {"filename": file.filename, "status": "parsed ✅", "text": text, "characters": len(text)}

@app.post("/api/ats/parse-offer")
async def parse_offer_pdf(file: UploadFile = File(...), _u: dict = Depends(require_auth)):
    file_bytes = await file.read()
    parsed = job_parser.parse_pdf(file_bytes)
    return {"filename": file.filename, "status": "parsed ✅", "offer": parsed,
            "offer_text": job_parser.to_job_offer_text(parsed)}

@app.post("/api/ats/parse-offer-text")
async def parse_offer_text(request: JobOfferTextRequest, _u: dict = Depends(require_auth)):
    parsed = job_parser.parse_text(request.raw_text)
    offer_data = {**parsed, "job_offer_id": request.job_offer_id, "raw_text": request.raw_text}
    store.save_offer(request.job_offer_id, offer_data)
    return {"job_offer_id": request.job_offer_id, "status": "parsed and saved ✅",
            "offer": parsed, "offer_text": job_parser.to_job_offer_text(parsed)}

# ── Offres (write = RH, read = tout le monde authentifié) ─────────────────────

@app.post("/api/ats/offers")
async def submit_offer(offer: JobOffer, _u: dict = Depends(require_role("RH"))):
    offer_data = offer.model_dump()
    store.save_offer(offer.job_offer_id, offer_data)
    return {"job_offer_id": offer.job_offer_id, "status": "saved ✅", "offer": offer_data}

@app.get("/api/ats/offers")
def list_offers(_u: dict = Depends(require_auth)):
    return {"total": len(store.list_offers()), "offers": store.list_offers()}

@app.get("/api/ats/offers/{job_offer_id}")
def get_offer(job_offer_id: str, _u: dict = Depends(require_auth)):
    offer = store.get_offer(job_offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail=f"Offre {job_offer_id} non trouvée")
    return offer

# ── Scoring (tout utilisateur authentifié) ────────────────────────────────────

@app.post("/api/ats/score", response_model=ScoreResponse)
async def score_candidate(request: ScoreRequest, _u: dict = Depends(require_auth)):
    rag_context = retriever.get_context(query=f"{request.cv_text} {request.job_offer.description}", k=5)
    job_offer_text = job_parser.to_job_offer_text(request.job_offer.model_dump())
    if not store.get_offer(request.job_offer_id):
        store.save_offer(request.job_offer_id, request.job_offer.model_dump())
    result = scorer.calculate(cv_text=request.cv_text, job_offer=job_offer_text, rag_context=rag_context)
    if len(hr_learner.feedback_history) > 0:
        result = hr_learner.apply_weights_to_score(result)
    store.save_score(candidate_id=request.candidate_id, job_offer_id=request.job_offer_id, score_result=result)
    return ScoreResponse(
        candidate_id=request.candidate_id, job_offer_id=request.job_offer_id,
        final_score=result["final_score"], original_score=result.get("original_score"),
        grade=result["grade"], recommendation=result["recommendation"],
        breakdown=result["breakdown"],
        explanation=result.get("explanations", result.get("explanation", {})),
        hr_adjusted=result.get("hr_adjusted", False), weights_applied=result.get("weights_applied")
    )

@app.post("/api/ats/score-bulk")
async def score_bulk(request: BulkScoreRequest, _u: dict = Depends(require_auth)):
    results, errors = [], []
    job_offer_text = job_parser.to_job_offer_text(request.job_offer.model_dump())
    if not store.get_offer(request.job_offer_id):
        store.save_offer(request.job_offer_id, request.job_offer.model_dump())
    for candidate in request.candidates:
        cid, cv = candidate.get("candidate_id"), candidate.get("cv_text", "")
        if not cid or not cv:
            errors.append({"candidate_id": cid, "error": "Données manquantes"}); continue
        try:
            rag_context = retriever.get_context(query=f"{cv} {request.job_offer.description}", k=5)
            result = scorer.calculate(cv_text=cv, job_offer=job_offer_text, rag_context=rag_context)
            if len(hr_learner.feedback_history) > 0:
                result = hr_learner.apply_weights_to_score(result)
            store.save_score(candidate_id=cid, job_offer_id=request.job_offer_id, score_result=result)
            results.append({"candidate_id": cid, "final_score": result["final_score"],
                            "grade": result["grade"], "recommendation": result["recommendation"]})
        except Exception as e:
            errors.append({"candidate_id": cid, "error": str(e)})
    return {"job_offer_id": request.job_offer_id, "processed": len(results), "errors": len(errors),
            "top_10": store.get_top_10(request.job_offer_id), "error_details": errors}

# ── Classement (tout utilisateur authentifié) ─────────────────────────────────

@app.get("/api/ats/ranking/{job_offer_id}")
def get_ranking(job_offer_id: str, limit: int = 10, _u: dict = Depends(require_auth)):
    top = store.get_top_10(job_offer_id) if limit >= 10 else store.get_all_scores(job_offer_id)[:limit]
    stats = store.get_stats(job_offer_id)
    return {"job_offer_id": job_offer_id, "total_candidates": stats["total"], "stats": stats,
            "hr_weights_applied": hr_learner.get_weights(),
            "ranking": [{"rank": i + 1, **c} for i, c in enumerate(top)]}

@app.get("/api/ats/scores/{candidate_id}")
def get_candidate_scores(candidate_id: str, _u: dict = Depends(require_auth)):
    scores = store.get_candidate_scores(candidate_id)
    return {"candidate_id": candidate_id, "total": len(scores), "scores": scores}

@app.get("/api/ats/stats/{job_offer_id}")
def get_stats(job_offer_id: str, _u: dict = Depends(require_auth)):
    stats = store.get_stats(job_offer_id)
    offer = store.get_offer(job_offer_id)
    return {"job_offer_id": job_offer_id,
            "offer_title": offer.get("title", "Inconnu") if offer else "Inconnu",
            "stats": stats, "hr_weights": hr_learner.get_weights()}

# ── Apprentissage RH (RH uniquement) ──────────────────────────────────────────

@app.post("/api/ats/feedback")
async def submit_hr_feedback(request: HRFeedbackRequest, _u: dict = Depends(require_role("RH"))):
    top10 = store.get_top_10(request.job_offer_id)
    if not top10:
        raise HTTPException(status_code=404, detail=f"Aucun score pour l'offre {request.job_offer_id}")
    result = hr_learner.record_feedback(
        job_offer_id=request.job_offer_id,
        chosen_candidate_id=request.chosen_candidate_id,
        rejected_candidates=request.rejected_candidate_ids,
        top10_scores=top10, reason=request.reason
    )
    return {"status": "ok", "message": "Préférences RH mises à jour ✅", "feedback_result": result,
            "impact": "Les prochains scorings utiliseront les nouveaux poids"}

@app.get("/api/ats/hr/weights")
def get_hr_weights(_u: dict = Depends(require_auth)):
    return {"weights": hr_learner.get_weights(),
            "default_weights": {"skills": 40, "experience": 30, "education": 20, "cosinus": 10},
            "preference_profile": hr_learner.preference_profile,
            "total_feedbacks": len(hr_learner.feedback_history),
            "feedback_history": hr_learner.feedback_history[-5:]}

@app.post("/api/ats/hr/reset-weights")
def reset_hr_weights(_u: dict = Depends(require_role("RH"))):
    return hr_learner.reset_weights()

# ── RAG (tout utilisateur authentifié) ───────────────────────────────────────

@app.get("/api/ats/rag/search")
def search_rag(query: str, _u: dict = Depends(require_auth)):
    context = retriever.get_context(query, k=3)
    return {"query": query, "context_found": context}

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_rabbitmq():
    start_consumer({"parser": parser, "job_parser": job_parser, "scorer": scorer,
                    "store": store, "hr_learner": hr_learner, "retriever": retriever})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
