# modules/storage/score_store.py
"""
Stockage des scores candidats en mémoire + persistance JSON.
Gère le classement Top 10 par offre d'emploi.
"""

import json
import os
from datetime import datetime
from typing import Optional

SCORES_FILE = os.getenv("SCORES_FILE", "data/scores.json")


class ScoreStore:
    """
    Base de données légère pour stocker les scores des candidats.
    Format: { job_offer_id: [ {candidate_id, final_score, ...}, ... ] }
    """

    def __init__(self):
        self._data: dict = {}      # scores par offre
        self._offers: dict = {}    # offres stockées
        self._load()

    # ─────────────────────────────────────────
    # PERSISTANCE
    # ─────────────────────────────────────────

    def _load(self):
        """Charge les données depuis le fichier JSON si il existe"""
        if os.path.exists(SCORES_FILE):
            try:
                with open(SCORES_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data = saved.get("scores", {})
                    self._offers = saved.get("offers", {})
                print(f"✅ ScoreStore: {sum(len(v) for v in self._data.values())} scores chargés")
            except Exception as e:
                print(f"⚠️ ScoreStore: impossible de charger {SCORES_FILE}: {e}")
                self._data = {}
                self._offers = {}

    def _save(self):
        """Persiste les données dans le fichier JSON"""
        try:
            os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump({"scores": self._data, "offers": self._offers}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ ScoreStore: impossible de sauvegarder: {e}")

    # ─────────────────────────────────────────
    # SCORES
    # ─────────────────────────────────────────

    def save_score(self, candidate_id: str, job_offer_id: str, score_result: dict):
        """
        Sauvegarde ou met à jour le score d'un candidat pour une offre.
        Si le candidat a déjà un score pour cette offre, on le remplace.
        """
        if job_offer_id not in self._data:
            self._data[job_offer_id] = []

        # Supprimer l'ancien score du même candidat s'il existe
        self._data[job_offer_id] = [
            s for s in self._data[job_offer_id]
            if s["candidate_id"] != candidate_id
        ]

        # Ajouter le nouveau score
        entry = {
            "candidate_id": candidate_id,
            "job_offer_id": job_offer_id,
            "final_score": score_result["final_score"],
            "grade": score_result["grade"],
            "recommendation": score_result["recommendation"],
            "breakdown": score_result["breakdown"],
            "explanation": score_result.get("explanations", score_result.get("explanation", {})),
            "scored_at": datetime.utcnow().isoformat()
        }

        self._data[job_offer_id].append(entry)
        self._save()

        print(f"💾 Score sauvegardé: candidat {candidate_id} → offre {job_offer_id} → {score_result['final_score']}/100")

    def get_top_10(self, job_offer_id: str) -> list:
        """
        Retourne les 10 meilleurs candidats pour une offre,
        triés par score décroissant. Applique les poids RH si disponibles.
        """
        candidates = self._data.get(job_offer_id, [])
        sorted_candidates = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
        return sorted_candidates[:10]

    def get_all_scores(self, job_offer_id: str) -> list:
        """Retourne tous les scores pour une offre, triés par score"""
        candidates = self._data.get(job_offer_id, [])
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)

    def get_candidate_scores(self, candidate_id: str) -> list:
        """Retourne tous les scores d'un candidat (toutes offres)"""
        results = []
        for job_offer_id, candidates in self._data.items():
            for entry in candidates:
                if entry["candidate_id"] == candidate_id:
                    results.append(entry)
        return sorted(results, key=lambda x: x["scored_at"], reverse=True)

    def get_stats(self, job_offer_id: str) -> dict:
        """Retourne les statistiques pour une offre"""
        candidates = self._data.get(job_offer_id, [])
        if not candidates:
            return {"total": 0, "avg_score": 0, "max_score": 0, "min_score": 0}

        scores = [c["final_score"] for c in candidates]
        return {
            "total": len(candidates),
            "avg_score": round(sum(scores) / len(scores), 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "grade_distribution": {
                "A": len([s for s in scores if s >= 85]),
                "B": len([s for s in scores if 70 <= s < 85]),
                "C": len([s for s in scores if 55 <= s < 70]),
                "D": len([s for s in scores if s < 55]),
            }
        }

    # ─────────────────────────────────────────
    # OFFRES D'EMPLOI
    # ─────────────────────────────────────────

    def save_offer(self, job_offer_id: str, offer_data: dict):
        """Stocke une offre d'emploi"""
        self._offers[job_offer_id] = {
            **offer_data,
            "created_at": datetime.utcnow().isoformat()
        }
        self._save()

    def get_offer(self, job_offer_id: str) -> Optional[dict]:
        """Récupère une offre d'emploi"""
        return self._offers.get(job_offer_id)

    def list_offers(self) -> list:
        """Liste toutes les offres"""
        return [
            {"job_offer_id": k, **v}
            for k, v in self._offers.items()
        ]


# Instance singleton
_store_instance: Optional[ScoreStore] = None


def get_score_store() -> ScoreStore:
    """Retourne l'instance singleton du store"""
    global _store_instance
    if _store_instance is None:
        _store_instance = ScoreStore()
    return _store_instance
