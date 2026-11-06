# modules/agents/experience_agent.py
import google.generativeai as genai
import json
import os
from .llm_config import generation_config

class ExperienceAgent:

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def analyze(self, cv_text: str, job_offer: str, rag_context: str) -> dict:
        """
        Analyse l'expérience professionnelle
        Retourne un score /30 avec explication
        """
        prompt = f"""
Tu es un expert RH spécialisé en recrutement technique.

CONTEXTE DE CONNAISSANCES :
{rag_context}

CV DU CANDIDAT :
{cv_text}

OFFRE D'EMPLOI :
{job_offer}

Analyse UNIQUEMENT l'expérience professionnelle :
- Nombre d'années d'expérience
- Pertinence des postes occupés
- Progression de carrière

Retourne UNIQUEMENT ce JSON valide :
{{
    "score": <nombre entre 0 et 30>,
    "years_found": <nombre d'années détectées>,
    "relevant_experience": ["poste 1 ✅", "poste 2 ✅"],
    "justification": "explication courte en français"
}}
"""
        try:
            response = self.model.generate_content(prompt, generation_config=generation_config())
            text = response.text.strip()

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)

        except Exception as e:
            print(f"❌ Erreur ExperienceAgent: {e}")
            return {
                "score": 0,
                "years_found": 0,
                "relevant_experience": [],
                "justification": f"Erreur analyse: {str(e)}"
            }