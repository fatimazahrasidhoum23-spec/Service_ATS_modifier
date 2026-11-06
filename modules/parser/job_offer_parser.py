# modules/parser/job_offer_parser.py
"""
Parseur d'offres d'emploi.
Reçoit une offre en texte libre, PDF ou JSON structuré
et extrait les informations clés avec Gemini.
"""

import google.generativeai as genai
import json
import os
import fitz  # PyMuPDF
import io

class JobOfferParser:

    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def parse_text(self, text: str) -> dict:
        """
        Analyse un texte d'offre d'emploi avec Gemini
        et retourne les informations structurées.
        """
        prompt = f"""
Tu es un expert RH. Analyse cette offre d'emploi et extrait les informations clés.

OFFRE D'EMPLOI :
{text}

Retourne UNIQUEMENT ce JSON valide (sans commentaires, sans markdown) :
{{
    "title": "Titre du poste",
    "description": "Description courte du poste (2-3 phrases)",
    "required_skills": ["skill1", "skill2", "skill3"],
    "nice_to_have_skills": ["skill4", "skill5"],
    "required_experience": <nombre d'années minimum, 0 si non précisé>,
    "required_education": "Bac+5 / Master / etc.",
    "soft_skills": ["leadership", "communication", "travail en équipe"],
    "contract_type": "CDI / CDD / Freelance / Stage / Alternance",
    "location": "Ville ou Remote",
    "domain": "Développement / Data / DevOps / Management / etc.",
    "seniority": "Junior / Mid-level / Senior / Lead",
    "salary_range": "Non précisé ou fourchette si mentionnée"
}}
"""
        try:
            response = self.model.generate_content(prompt)
            text_response = response.text.strip()

            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()

            parsed = json.loads(text_response)
            return parsed

        except Exception as e:
            print(f"❌ Erreur JobOfferParser: {e}")
            # Retourner une structure minimale en cas d'erreur
            return {
                "title": "Offre non parsée",
                "description": text[:200],
                "required_skills": [],
                "nice_to_have_skills": [],
                "required_experience": 0,
                "required_education": "Non précisé",
                "soft_skills": [],
                "contract_type": "Non précisé",
                "location": "Non précisé",
                "domain": "Non précisé",
                "seniority": "Non précisé",
                "salary_range": "Non précisé"
            }

    def parse_pdf(self, file_bytes: bytes) -> dict:
        """Extrait le texte d'un PDF puis le parse"""
        text = ""
        try:
            pdf = fitz.open(stream=file_bytes, filetype="pdf")
            for page in pdf:
                text += page.get_text()
            pdf.close()
        except Exception as e:
            raise ValueError(f"Impossible de lire le PDF: {e}")

        if not text.strip():
            raise ValueError("Le PDF est vide ou ne contient pas de texte extractible")

        return self.parse_text(text.strip())

    def to_job_offer_text(self, parsed: dict) -> str:
        """
        Convertit un dictionnaire parsé en texte pour les agents.
        Inclut les soft skills pour l'adaptateur RH.
        """
        skills_str = ", ".join(parsed.get("required_skills", []))
        nice_str = ", ".join(parsed.get("nice_to_have_skills", []))
        soft_str = ", ".join(parsed.get("soft_skills", []))

        return f"""
Titre: {parsed.get('title', '')}
Description: {parsed.get('description', '')}
Compétences requises: {skills_str}
Compétences souhaitées: {nice_str}
Soft skills: {soft_str}
Expérience requise: {parsed.get('required_experience', 0)} ans
Formation requise: {parsed.get('required_education', '')}
Domaine: {parsed.get('domain', '')}
Niveau: {parsed.get('seniority', '')}
Type de contrat: {parsed.get('contract_type', '')}
Localisation: {parsed.get('location', '')}
""".strip()
