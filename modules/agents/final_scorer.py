# modules/agents/final_scorer.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .skill_agent import SkillAgent
from .experience_agent import ExperienceAgent
from .education_agent import EducationAgent
from modules.privacy import anonymize
import time

class FinalScorer:

    def __init__(self):
        self.skill_agent      = SkillAgent()
        self.experience_agent = ExperienceAgent()
        self.education_agent  = EducationAgent()

    def calculate_cosine(self, cv_text: str, job_offer: str) -> float:
        """
        Calcule la similarité cosinus entre CV et offre
        Retourne un score entre 0 et 10
        """
        try:
            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform([cv_text, job_offer])
            similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
            return round(similarity * 10, 2)
        except:
            return 0.0

    def calculate(self, cv_text: str, job_offer: str, rag_context: str) -> dict:
        """
        Orchestre tous les agents et calcule le score final
        """
        print("🤖 Lancement des agents IA...")

        # Protection des données : le LLM ne reçoit ni nom, ni e-mail, ni téléphone, ni liens
        cv_text = anonymize(cv_text)

        # Lancer les 3 agents avec délai entre chaque
        # pour éviter le quota Gemini
        skill_result = self.skill_agent.analyze(cv_text, job_offer, rag_context)
        time.sleep(4)

        experience_result = self.experience_agent.analyze(cv_text, job_offer, rag_context)
        time.sleep(4)

        education_result = self.education_agent.analyze(cv_text, job_offer, rag_context)

        # Un agent en erreur (quota 429, JSON invalide...) renvoie 0 : on le signale
        agent_errors = [
            name for name, r in (("skills", skill_result), ("experience", experience_result),
                                 ("education", education_result))
            if str(r.get("justification", "")).startswith("Erreur analyse")
        ]
        if agent_errors:
            print(f"⚠️ Agents en erreur : {agent_errors} — score incomplet")

        # Calculer le cosinus
        cosine_score = self.calculate_cosine(cv_text, job_offer)

        # Score final
        final_score = (
            skill_result["score"] +        # /40
            experience_result["score"] +   # /30
            education_result["score"] +    # /20
            cosine_score                   # /10
        )

        final_score = min(round(final_score, 2), 100)

        # Déterminer le grade
        if final_score >= 85:
            grade = "A"
            recommendation = "HIGHLY RECOMMENDED"
        elif final_score >= 70:
            grade = "B"
            recommendation = "RECOMMENDED"
        elif final_score >= 55:
            grade = "C"
            recommendation = "MAYBE"
        else:
            grade = "D"
            recommendation = "NOT RECOMMENDED"

        print(f"✅ Score final : {final_score}/100 → Grade {grade}")

        return {
            "final_score": final_score,
            "agent_errors": agent_errors,
            "grade": grade,
            "recommendation": recommendation,
            "breakdown": {
                "skills": {
                    "score": skill_result["score"],
                    "max": 40,
                    "matched": skill_result.get("matched_skills", []),
                    "missing": skill_result.get("missing_skills", [])
                },
                "experience": {
                    "score": experience_result["score"],
                    "max": 30,
                    "years": experience_result.get("years_found", 0),
                    "relevant": experience_result.get("relevant_experience", [])
                },
                "education": {
                    "score": education_result["score"],
                    "max": 20,
                    "degree": education_result.get("degree_found", ""),
                    "keywords_matched": education_result.get("keywords_matched", []),
                    "keywords_missing": education_result.get("keywords_missing", [])
                },
                "cosinus": {
                    "score": cosine_score,
                    "max": 10
                }
            },
            "explanations": {
                "skills":     skill_result.get("justification", ""),
                "experience": experience_result.get("justification", ""),
                "education":  education_result.get("justification", "")
            }
        }