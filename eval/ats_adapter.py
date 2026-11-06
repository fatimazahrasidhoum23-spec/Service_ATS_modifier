"""
Pont entre les scripts d'évaluation et le vrai pipeline du service ATS
(CVParser → RAG → 3 agents Gemini → score final). Rien à modifier ici.

Marche sur ton PC (sans Docker) ou dans le conteneur ats-service.
Il faut seulement la variable d'environnement GEMINI_API_KEY.
"""

import sys
import time
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Hors Docker (sur ton PC), la base ChromaDB est créée dans eval/chroma_data
if not Path("/app").exists():
    os.environ.setdefault("CHROMA_PATH", str(ROOT / "eval" / "chroma_data"))

from modules.parser.cv_parser import CVParser                 # noqa: E402
from modules.parser.job_offer_parser import JobOfferParser    # noqa: E402
from modules.rag.retriever import RAGRetriever                # noqa: E402
from modules.rag.knowledge_base import knowledge_documents    # noqa: E402
from modules.agents.final_scorer import FinalScorer           # noqa: E402
from modules.privacy import anonymize                         # noqa: E402

_cv_parser = CVParser()
_job_parser = JobOfferParser()
_scorer = FinalScorer()
_retriever = RAGRetriever()
if not _retriever.is_indexed():
    _retriever.index_knowledge_base(knowledge_documents)

_offer_cache: dict[str, str] = {}


def read_text(path: str | Path) -> str:
    """CV ou offre : .pdf / .docx (même parseur que le service) ou .txt."""
    path = Path(path)
    if path.suffix.lower() in (".pdf", ".docx"):
        return _cv_parser.parse(path.read_bytes(), path.name)
    return path.read_text(encoding="utf-8")


def _offer_text(raw_offer: str) -> str:
    """Structure l'offre une seule fois (1 appel Gemini), comme le consumer RabbitMQ."""
    if raw_offer not in _offer_cache:
        parsed = _job_parser.parse_text(raw_offer)
        _offer_cache[raw_offer] = _job_parser.to_job_offer_text(parsed)
    return _offer_cache[raw_offer]


def score_cv(cv_text: str, raw_offer: str, retries: int = 3) -> float:
    """Score final /100 du système complet. Réessaie si un agent échoue (quota 429...)."""
    job_offer = _offer_text(raw_offer)
    rag_context = _retriever.get_context(query=f"{cv_text} {raw_offer}", k=5)
    for attempt in range(1, retries + 1):
        result = _scorer.calculate(cv_text=cv_text, job_offer=job_offer, rag_context=rag_context)
        if not result.get("agent_errors"):
            return float(result["final_score"])
        wait = 30 * attempt
        print(f"   ⚠️ Agents en erreur {result['agent_errors']} → nouvel essai dans {wait}s")
        time.sleep(wait)
    raise RuntimeError("Les agents Gemini échouent toujours (clé API ? quota ?). Score non fiable, test arrêté.")


def tfidf_score(cv_text: str, raw_offer: str) -> float:
    """Baseline : la similarité cosinus TF-IDF seule (celle du service), ramenée sur 100."""
    return _scorer.calculate_cosine(anonymize(cv_text), _offer_text(raw_offer)) * 10
