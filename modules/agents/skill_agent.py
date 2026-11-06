# modules/agents/skill_agent.py
import google.generativeai as genai
import json
import os
from .llm_config import generation_config

class SkillAgent:

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def analyze(self, cv_text: str, job_offer: str, rag_context: str) -> dict:
        """
        Analyse les compétences techniques
        Retourne un score /40 avec explication
        """
        prompt = f"""
Tu es un expert RH spécialisé en recrutement technique.

CONTEXTE DE CONNAISSANCES (synonymes et équivalences) :
{rag_context}

CV DU CANDIDAT :
{cv_text}

OFFRE D'EMPLOI :
{job_offer}

Analyse UNIQUEMENT les compétences techniques.
Utilise le contexte pour détecter les synonymes.
Ex: "ML" dans le CV = "Machine Learning" dans l'offre.

Retourne UNIQUEMENT ce JSON valide :
{{
    "score": <nombre entre 0 et 40>,
    "matched_skills": ["Python ✅", "Docker ✅"],
    "missing_skills": ["Kubernetes ❌"],
    "justification": "explication courte en français"
}}
"""
        try:
            response = self.model.generate_content(prompt, generation_config=generation_config())
            text = response.text.strip()

            # Nettoyer la réponse si nécessaire
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)

        except Exception as e:
            print(f"❌ Erreur SkillAgent: {e}")
            return {
                "score": 0,
                "matched_skills": [],
                "missing_skills": [],
                "justification": f"Erreur analyse: {str(e)}"
            }