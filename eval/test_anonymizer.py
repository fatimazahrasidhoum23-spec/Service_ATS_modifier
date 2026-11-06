"""
TEST 0 — Anonymisation (sans Gemini, instantané).

Usage :
    docker exec -it ats-service python eval/test_anonymizer.py                       # exemples intégrés
    docker exec -it ats-service python eval/test_anonymizer.py eval/data/mon_cv.pdf  # un vrai CV
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.privacy import anonymize  # noqa: E402

CASES = [
    ("SIDHOUM Fatima Zahra\nOujda, Maroc • +212 633488478 • fatima.z@gmail.com\n"
     "github.com/fatima-dev • Python, FastAPI, RAG • 2022 – 2027",
     ["SIDHOUM", "Fatima", "633488478", "fatima.z@gmail.com", "github.com/fatima-dev"],
     ["Python", "FastAPI", "RAG", "2022", "2027", "Oujda"]),
    ("Ahmed El Amrani\nTél : 06 12 34 56 78 — linkedin.com/in/ahmed\nExpérience : 3 ans Java, Spring Boot",
     ["Ahmed", "Amrani", "06 12 34 56 78", "linkedin.com/in/ahmed"],
     ["Java", "Spring Boot", "3 ans"]),
]

if len(sys.argv) > 1:
    from modules.parser.cv_parser import CVParser
    p = Path(sys.argv[1])
    text = CVParser().parse(p.read_bytes(), p.name) if p.suffix in (".pdf", ".docx") else p.read_text("utf-8")
    print("──── AVANT (début) ────\n" + text[:600])
    print("\n──── APRÈS (début) ────\n" + anonymize(text)[:600])
    sys.exit(0)

ok = True
for text, must_hide, must_keep in CASES:
    out = anonymize(text)
    for s in must_hide:
        if s.lower() in out.lower():
            ok = False
            print(f"❌ Encore visible : {s!r}")
    for s in must_keep:
        if s not in out:
            ok = False
            print(f"❌ Supprimé à tort : {s!r}")
    print(out, "\n")
print("✅ Anonymisation OK" if ok else "❌ Anonymisation à corriger")
