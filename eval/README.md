# Évaluation du service ATS

Tous les tests se lancent **dans le conteneur** `ats-service` (la clé Gemini et ChromaDB y sont).

## 0. Préparer
1. À côté de `docker-compose.global.yml`, crée un fichier `.env` :
   ```
   GEMINI_API_KEY=ta_cle_gemini
   ```
   Ajoute `.env` dans `.gitignore` (ne jamais pousser la clé sur GitHub).
2. Mets tes fichiers dans `Service_ATS/eval/data/` :
   - `offre.txt` (un exemple est fourni)
   - `mon_cv.pdf` (le CV à tester)
   - `cvs/` + `classement_humain.csv` (pour le test 3, voir `classement_humain_EXEMPLE.csv`)
3. Reconstruis et démarre :
   ```
   docker compose -f docker-compose.global.yml up -d --build rabbitmq ats-service
   ```

## 1. Anonymisation (instantané, sans Gemini)
```
docker exec -it ats-service python eval/test_anonymizer.py
docker exec -it ats-service python eval/test_anonymizer.py eval/data/mon_cv.pdf
```

## 2. Stabilité du score
```
docker exec -it ats-service python eval/test_stabilite.py eval/data/mon_cv.pdf eval/data/offre.txt --runs 5
```
Résultat : moyenne ± écart-type → `eval/resultats_stabilite.csv`.

Comparaison avec température 0 : mets `LLM_TEMPERATURE=0` dans `.env`, relance `up -d ats-service`, refais le test.

## 3. Classement humain vs système vs TF-IDF
Classe les CV toi-même **avant** de lancer le test, puis :
```
docker exec -it ats-service python eval/test_classement.py eval/data/offre.txt
```
Résultat : corrélations de Spearman → `eval/resultats_classement.csv`.

## Récupérer les fichiers de résultats
```
docker cp ats-service:/app/eval/resultats_stabilite.csv .
docker cp ats-service:/app/eval/resultats_classement.csv .
```
