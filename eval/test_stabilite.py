"""
TEST 1 — Stabilité du score.
Score le même CV N fois et mesure la variation (le LLM n'est pas déterministe).

Usage :
    docker exec -it ats-service python eval/test_stabilite.py eval/data/mon_cv.pdf eval/data/offre.txt --runs 5
Résultat : moyenne, écart-type, min, max + fichier eval/resultats_stabilite.csv
"""

import argparse
import csv
import statistics
import time
from pathlib import Path

from ats_adapter import read_text, score_cv

p = argparse.ArgumentParser()
p.add_argument("cv")
p.add_argument("offre")
p.add_argument("--runs", type=int, default=5)
p.add_argument("--pause", type=float, default=10, help="secondes entre deux scorings (quota Gemini)")
args = p.parse_args()

cv, job = read_text(args.cv), read_text(args.offre)
scores = []
for i in range(args.runs):
    s = score_cv(cv, job)
    scores.append(s)
    print(f"Exécution {i + 1}/{args.runs} : {s:.2f}")
    time.sleep(args.pause)

mean, std = statistics.mean(scores), statistics.stdev(scores) if len(scores) > 1 else 0.0
print(f"\nMoyenne : {mean:.2f} | Écart-type : ±{std:.2f} | Min : {min(scores):.2f} | Max : {max(scores):.2f}")

with open(Path(__file__).parent / "resultats_stabilite.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["execution", "score"])
    w.writerows(enumerate(scores, 1))
    w.writerow([])
    w.writerow(["moyenne", round(mean, 2)])
    w.writerow(["ecart_type", round(std, 2)])
