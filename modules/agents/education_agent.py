# modules/agents/education_agent.py
import google.generativeai as genai
import json
import os
from .llm_config import generation_config

class EducationAgent:

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def analyze(self, cv_text: str, job_offer: str, rag_context: str) -> dict:
        """
        Analyse la formation et les mots-clés
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

Analyse la formation académique et les mots-clés :
- Niveau de diplôme (Bac+2, Bac+3, Bac+5...)
- Domaine d'études
- Certifications
- Mots-clés importants de l'offre trouvés dans le CV

Retourne UNIQUEMENT ce JSON valide :
{{
    "score": <nombre entre 0 et 30>,
    "degree_found": "Master Informatique",
    "keywords_matched": ["agile ✅", "scrum ✅"],
    "keywords_missing": ["PMP ❌"],
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
            print(f"❌ Erreur EducationAgent: {e}")
            return {
                "score": 0,
                "degree_found": "",
                "keywords_matched": [],
                "keywords_missing": [],
                "justification": f"Erreur analyse: {str(e)}"
            }