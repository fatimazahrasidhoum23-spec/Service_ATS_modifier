# modules/privacy/anonymizer.py
"""
Anonymisation d'un CV avant l'envoi au LLM (Gemini).

Masque : e-mails, téléphones, liens (LinkedIn, GitHub, sites web) et le nom
du candidat. Le scoring n'a pas besoin de ces informations, et les retirer
limite aussi le risque de biais lié au nom.

Le nom est masqué de deux façons :
  1. s'il est fourni (candidate_name) ;
  2. sinon, par heuristique : la première ligne non vide du CV, si elle
     ressemble à un nom (2 à 5 mots, uniquement des lettres).

Limite connue : un nom qui apparaît ailleurs sans être fourni n'est pas
détecté. Pour aller plus loin : Microsoft Presidio (NER).
"""

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL = re.compile(r"(https?://\S+|www\.\S+|\b[\w-]+\.(com|ma|fr|io|dev|org|net)/\S*)", re.I)
# Téléphones : +212 6 33 48 84 78, 06-12-34-56-78, +33 6 12 34 56 78, 0612345678 ...
PHONE = re.compile(r"(?<!\d)(\+\d{1,3}[\s.-]?)?(\(?0\)?[\s.-]?)?[1-9](?:[\s.-]?\d{2}){4}(?!\d)")
NAME_WORD = re.compile(r"^[^\W\d_][^\W\d_'’-]*(?:['’-][^\W\d_]+)*$")


def _looks_like_name(line: str) -> bool:
    words = line.split()
    return 2 <= len(words) <= 5 and len(line) <= 60 and all(NAME_WORD.match(w) for w in words)


def anonymize(text: str, candidate_name: str | None = None) -> str:
    if not text:
        return text

    names = []
    if candidate_name:
        names.append(candidate_name)
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    if _looks_like_name(first_line):
        names.append(first_line)

    text = EMAIL.sub("[EMAIL]", text)
    text = URL.sub("[LIEN]", text)
    text = PHONE.sub("[TEL]", text)

    # nom complet puis chaque partie (prénom, nom), les plus longues d'abord
    parts = set()
    for n in names:
        parts.add(n)
        parts.update(w for w in n.split() if len(w) > 2)
    for part in sorted(parts, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(part) + r"(?!\w)", "[NOM]", text, flags=re.I)
    return text
