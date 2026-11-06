"""
TESTS 2 et 3 — Accord avec un classement humain + comparaison avec la baseline TF-IDF.

Préparation :
  1. Mets 8 à 10 CV dans eval/data/cvs/ (.pdf, .docx ou .txt).
  2. AVANT de lancer le script, classe-les toi-même pour l'offre et
     écris eval/data/classement_humain.csv :
         fichier,rang
         cv_ahmed.pdf,1
         cv_sara.pdf,2
         ...
     (rang 1 = meilleur candidat)

Usage :
    docker exec -it ats-service python eval/test_classement.py eval/data/offre.txt
Résultat : corrélation de Spearman (système vs humain, TF-IDF vs humain)
           + fichier eval/resultats_classement.csv
"""

import argparse
import csv
import time
from pathlib import Path

from scipy.stats import spearmanr

from ats_adapter import read_text, score_cv, tfidf_score

p = argparse.ArgumentParser()
p.add_argument("offre")
p.add_argument("--cvs", default="eval/data/cvs")
p.add_argument("--humain", default="eval/data/classement_humain.csv")
p.add_argument("--pause", type=float, default=10)
args = p.parse_args()

job = read_text(args.offre)
with open(args.humain, encoding="utf-8") as f:
    human = {row["fichier"]: int(row["rang"]) for row in csv.DictReader(f)}

rows = []
for name, rank in human.items():
    cv = read_text(Path(args.cvs) / name)
    s_sys = score_cv(cv, job)
    s_tfidf = tfidf_score(cv, job)
    rows.append((name, rank, round(s_sys, 2), round(s_tfidf, 2)))
    print(f"{name:30s} rang humain {rank:2d} | système {s_sys:6.2f} | TF-IDF {s_tfidf:6.2f}")
    time.sleep(args.pause)

# Rang 1 = meilleur, donc on compare avec -rang (score élevé = bon rang)
neg_ranks = [-r[1] for r in rows]
rho_sys, p_sys = spearmanr(neg_ranks, [r[2] for r in rows])
rho_tf, p_tf = spearmanr(neg_ranks, [r[3] for r in rows])

print(f"\nSpearman système complet vs humain : ρ = {rho_sys:.2f} (p = {p_sys:.3f})")
print(f"Spearman TF-IDF seul      vs humain : ρ = {rho_tf:.2f} (p = {p_tf:.3f})")
print("ρ proche de 1 = même ordre que toi ; proche de 0 = aucun accord.")

with open(Path(__file__).parent / "resultats_classement.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["fichier", "rang_humain", "score_systeme", "score_tfidf"])
    w.writerows(rows)
    w.writerow([])
    w.writerow(["spearman_systeme", round(rho_sys, 3)])
    w.writerow(["spearman_tfidf", round(rho_tf, 3)])
