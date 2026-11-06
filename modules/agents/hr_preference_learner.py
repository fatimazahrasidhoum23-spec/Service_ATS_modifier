# modules/agents/hr_preference_learner.py
"""
Adaptateur de préférences RH.

Quand RH choisit le profil 98 plutôt que 99,
ce module analyse POURQUOI et ajuste les poids
pour les prochains scorings.

Exemple :
- RH choisit toujours les profils avec fort score "soft skills"
  → augmenter le poids "soft_skills" dans le FinalScorer
- RH préfère DevOps à Python
  → le RAG va enrichir les requêtes DevOps
"""

import json
import os
from collections import defaultdict
from typing import Optional
import google.generativeai as genai

PREFS_FILE = os.getenv("PREFS_FILE", "data/hr_preferences.json")

# Poids par défaut (doivent sommer à 100)
DEFAULT_WEIGHTS = {
    "skills": 40,       # compétences techniques
    "experience": 30,   # expérience professionnelle
    "education": 20,    # formation
    "cosinus": 10,      # similarité cosinus
}


class HRPreferenceLearner:
    """
    Apprend les préférences RH à partir des choix effectués.
    Ajuste les poids de scoring en conséquence.
    """

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        self.weights = DEFAULT_WEIGHTS.copy()
        self.feedback_history: list = []
        self.preference_profile: dict = {}

        self._load()

    # ─────────────────────────────────────────
    # PERSISTANCE
    # ─────────────────────────────────────────

    def _load(self):
        """Charge les préférences depuis le fichier JSON"""
        if os.path.exists(PREFS_FILE):
            try:
                with open(PREFS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.weights = saved.get("weights", DEFAULT_WEIGHTS.copy())
                    self.feedback_history = saved.get("feedback_history", [])
                    self.preference_profile = saved.get("preference_profile", {})
                print(f"✅ HRPreferenceLearner: {len(self.feedback_history)} feedbacks chargés")
            except Exception as e:
                print(f"⚠️ HRPreferenceLearner: impossible de charger: {e}")

    def _save(self):
        """Persiste les préférences"""
        try:
            os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
            with open(PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "weights": self.weights,
                    "feedback_history": self.feedback_history,
                    "preference_profile": self.preference_profile
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ HRPreferenceLearner: impossible de sauvegarder: {e}")

    # ─────────────────────────────────────────
    # APPRENTISSAGE
    # ─────────────────────────────────────────

    def record_feedback(
        self,
        job_offer_id: str,
        chosen_candidate_id: str,
        rejected_candidates: list,
        top10_scores: list,
        reason: Optional[str] = None
    ) -> dict:
        """
        Enregistre le choix RH et met à jour les poids.

        chosen_candidate_id : candidat que RH a sélectionné
        rejected_candidates : candidats ignorés (du top 10)
        top10_scores        : liste des 10 meilleurs avec leurs breakdowns
        reason              : raison textuelle optionnelle (ex: "préfère soft skills")
        """
        # Trouver le profil choisi et les profils rejetés
        chosen = next((c for c in top10_scores if c["candidate_id"] == chosen_candidate_id), None)
        rejected = [c for c in top10_scores if c["candidate_id"] in rejected_candidates]

        if not chosen:
            return {"status": "error", "message": "Candidat choisi non trouvé dans le top 10"}

        # Construire l'historique
        feedback_entry = {
            "job_offer_id": job_offer_id,
            "chosen": {
                "candidate_id": chosen_candidate_id,
                "final_score": chosen["final_score"],
                "breakdown": chosen.get("breakdown", {})
            },
            "rejected": [
                {
                    "candidate_id": r["candidate_id"],
                    "final_score": r["final_score"],
                    "breakdown": r.get("breakdown", {})
                }
                for r in rejected[:3]  # garder les 3 premiers rejetés
            ],
            "reason": reason or "Non précisé"
        }
        self.feedback_history.append(feedback_entry)

        # Analyser les patterns et mettre à jour les poids
        updated_weights = self._analyze_and_update_weights(
            chosen=chosen,
            rejected=rejected,
            reason=reason
        )

        self._save()

        return {
            "status": "ok",
            "message": "Préférences mises à jour",
            "new_weights": updated_weights,
            "analysis": self.preference_profile
        }

    def _analyze_and_update_weights(
        self,
        chosen: dict,
        rejected: list,
        reason: Optional[str] = None
    ) -> dict:
        """
        Compare les scores breakdown du candidat choisi vs rejetés
        pour déduire les critères préférés de RH.
        """
        if not rejected:
            return self.weights

        chosen_breakdown = chosen.get("breakdown", {})

        # Pour chaque critère, comparer si le choisi est > ou < les rejetés
        criteria_deltas = defaultdict(float)

        for rejected_candidate in rejected:
            rej_breakdown = rejected_candidate.get("breakdown", {})

            for criterion in ["skills", "experience", "education", "cosinus"]:
                chosen_score = self._get_normalized_score(chosen_breakdown, criterion)
                rejected_score = self._get_normalized_score(rej_breakdown, criterion)

                # Si RH a choisi quelqu'un avec un score inférieur sur ce critère,
                # ce critère est MOINS important pour RH
                delta = chosen_score - rejected_score
                criteria_deltas[criterion] += delta

        # Ajuster les poids
        adjustment_strength = 2.0  # force de l'ajustement par feedback

        for criterion, delta in criteria_deltas.items():
            if delta > 0:
                # Le choisi est meilleur sur ce critère → légèrement plus important
                self.weights[criterion] = min(
                    self.weights[criterion] + adjustment_strength,
                    60  # plafond par critère
                )
            elif delta < 0:
                # Le choisi est moins bon sur ce critère → moins important pour RH
                self.weights[criterion] = max(
                    self.weights[criterion] - adjustment_strength,
                    5   # plancher par critère
                )

        # Renormaliser pour que la somme = 100
        self._normalize_weights()

        # Mettre à jour le profil de préférence
        self._update_preference_profile(reason)

        print(f"📊 Poids RH mis à jour: {self.weights}")
        return self.weights

    def _get_normalized_score(self, breakdown: dict, criterion: str) -> float:
        """Normalise le score d'un critère sur 100"""
        if criterion not in breakdown:
            return 0.0
        score = breakdown[criterion].get("score", 0)
        max_score = breakdown[criterion].get("max", 1)
        return score / max_score if max_score > 0 else 0.0

    def _normalize_weights(self):
        """Renormalise les poids pour qu'ils somment à 100"""
        total = sum(self.weights.values())
        if total == 0:
            self.weights = DEFAULT_WEIGHTS.copy()
            return
        factor = 100 / total
        for k in self.weights:
            self.weights[k] = round(self.weights[k] * factor, 1)

    def _update_preference_profile(self, reason: Optional[str]):
        """Met à jour le profil textuel des préférences RH"""
        # Identifier le critère le plus pondéré
        max_criterion = max(self.weights, key=self.weights.get)
        min_criterion = min(self.weights, key=self.weights.get)

        self.preference_profile = {
            "total_feedbacks": len(self.feedback_history),
            "priority_criterion": max_criterion,
            "least_priority_criterion": min_criterion,
            "current_weights": self.weights,
            "last_reason": reason or "Non précisé",
            "profile_summary": self._generate_profile_summary()
        }

    def _generate_profile_summary(self) -> str:
        """Génère un résumé textuel du profil de préférence"""
        w = self.weights
        parts = []

        if w.get("skills", 0) > 35:
            parts.append("RH valorise fortement les compétences techniques")
        elif w.get("skills", 0) < 25:
            parts.append("RH accorde moins d'importance aux compétences techniques")

        if w.get("experience", 0) > 30:
            parts.append("l'expérience professionnelle est prioritaire")
        elif w.get("experience", 0) < 20:
            parts.append("l'expérience est moins déterminante")

        if w.get("education", 0) > 25:
            parts.append("la formation académique est importante")

        return ". ".join(parts) if parts else "Profil de préférences en cours d'apprentissage."

    # ─────────────────────────────────────────
    # APPLICATION DES POIDS
    # ─────────────────────────────────────────

    def apply_weights_to_score(self, score_result: dict) -> dict:
        """
        Repondère un score existant avec les poids appris.
        Retourne un nouveau score ajusté.

        Le score original est calculé avec les poids par défaut.
        On recalcule avec les poids personnalisés RH.
        """
        breakdown = score_result.get("breakdown", {})

        # Récupérer les scores bruts (sur leur max respectif)
        skills_raw = breakdown.get("skills", {}).get("score", 0)       # /40
        exp_raw = breakdown.get("experience", {}).get("score", 0)      # /30
        edu_raw = breakdown.get("education", {}).get("score", 0)       # /20
        cos_raw = breakdown.get("cosinus", {}).get("score", 0)         # /10

        # Normaliser chaque score sur 100
        skills_pct = skills_raw / 40 if skills_raw else 0
        exp_pct = exp_raw / 30 if exp_raw else 0
        edu_pct = edu_raw / 20 if edu_raw else 0
        cos_pct = cos_raw / 10 if cos_raw else 0

        # Appliquer les poids RH
        w = self.weights
        adjusted_score = (
            skills_pct * w.get("skills", 40) +
            exp_pct * w.get("experience", 30) +
            edu_pct * w.get("education", 20) +
            cos_pct * w.get("cosinus", 10)
        )

        adjusted_score = min(round(adjusted_score, 2), 100)

        # Déterminer le nouveau grade
        if adjusted_score >= 85:
            grade = "A"
            recommendation = "HIGHLY RECOMMENDED"
        elif adjusted_score >= 70:
            grade = "B"
            recommendation = "RECOMMENDED"
        elif adjusted_score >= 55:
            grade = "C"
            recommendation = "MAYBE"
        else:
            grade = "D"
            recommendation = "NOT RECOMMENDED"

        return {
            **score_result,
            "final_score": adjusted_score,
            "original_score": score_result.get("final_score"),
            "grade": grade,
            "recommendation": recommendation,
            "weights_applied": self.weights,
            "hr_adjusted": True
        }

    def get_weights(self) -> dict:
        """Retourne les poids actuels"""
        return self.weights.copy()

    def reset_weights(self):
        """Réinitialise les poids par défaut"""
        self.weights = DEFAULT_WEIGHTS.copy()
        self.feedback_history = []
        self.preference_profile = {}
        self._save()
        return {"status": "ok", "weights": self.weights}


# Instance singleton
_learner_instance: Optional[HRPreferenceLearner] = None


def get_hr_learner() -> HRPreferenceLearner:
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = HRPreferenceLearner()
    return _learner_instance
