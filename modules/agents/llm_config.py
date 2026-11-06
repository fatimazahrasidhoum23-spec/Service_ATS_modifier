# modules/agents/llm_config.py
"""
Configuration commune des appels Gemini.

LLM_TEMPERATURE (variable d'environnement, optionnelle) :
  - non définie → comportement par défaut de Gemini (comme avant)
  - "0"         → réponses plus stables (utile pour les tests de stabilité)
"""

import os


def generation_config():
    value = os.getenv("LLM_TEMPERATURE")
    if value in (None, ""):
        return None
    return {"temperature": float(value)}
