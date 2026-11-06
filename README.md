# Service ATS — Scoring explicable de CV par LLM et RAG

> **EN —** An AI microservice that scores CVs against job offers using three specialized LLM agents (Gemini), a RAG knowledge base (ChromaDB) and a TF-IDF baseline. It anonymizes personal data before any LLM call and ships with an evaluation suite that measures score stability and detects silent agent failures.

Service développé dans le cadre de mon **Projet de Fin d'Année (PFA)** : une plateforme de recrutement en microservices réalisée en équipe de 5. Ce dépôt contient **le service IA, dont j'étais responsable**.

---

## Le problème

Un recruteur reçoit des centaines de CV. Le tri manuel est long, subjectif, et le simple matching de mots-clés rate les bons profils (« ML » ≠ « Machine Learning »). L'objectif : un score **rapide, sémantique et explicable**, dimension par dimension.

## Comment ça marche

```
CV (PDF/DOCX) ──► Extraction du texte ──► Anonymisation ──┐
                                                          ├──► 3 agents LLM ──► Score final /100
Offre d'emploi ──► Structuration (LLM) ───────────────────┤     + justifications
                                                          │
Base RAG (85 documents de synonymes IT) ──► Contexte ─────┘
```

| Composant | Rôle | Points |
|---|---|---|
| **Agent Compétences** | compétences trouvées / manquantes | /40 |
| **Agent Expérience** | années et pertinence de l'expérience | /30 |
| **Agent Formation** | niveau et adéquation du diplôme | /20 |
| **Similarité TF-IDF** | mesure lexicale objective et reproductible | /10 |

- **RAG** : 85 documents d'équivalences techniques (langages, frameworks, DevOps, IA, niveaux de séniorité…), indexés dans ChromaDB avec `all-MiniLM-L6-v2`.
- **Explicabilité** : chaque agent renvoie un sous-score **et une justification** en langage naturel.
- **Apprentissage des préférences RH** : les poids s'ajustent selon les choix du recruteur.
- **Intégration** : API REST (FastAPI) sécurisée par JWT avec rôles, et traitement asynchrone via RabbitMQ.

## Protection des données

Avant tout appel au LLM, le CV est **anonymisé** (`modules/privacy/anonymizer.py`) : nom, e-mail, téléphone et liens sont masqués. Le scoring n'en a pas besoin, et les retirer limite aussi le risque de biais lié au nom. Les secrets (clé API, JWT) sont lus uniquement depuis l'environnement.

## Évaluation

Le dossier [`eval/`](eval/) contient les scripts d'évaluation, branchés sur le vrai pipeline.

**Stabilité du score** — même CV, même offre, plusieurs exécutions :

| Exécution | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Score /100 | 93,2 | 93,2 | 97,2 | 87,2 |

**Moyenne 92,7 ± 4,1 points** (écart max : 10 points). Le LLM n'étant pas déterministe, un même CV peut changer de note ; près d'un seuil de grade, cela peut changer la recommandation.

**Découverte : des échecs silencieux.** Lors d'une 5ᵉ exécution, deux agents ont reçu une erreur de quota API (429) et ont renvoyé 0 : le score est tombé à **40,2 (grade D) au lieu de ~93**, sans aucune alerte. Le service détecte désormais ces erreurs (`agent_errors`) au lieu de les enregistrer comme un vrai score.

Autres scripts disponibles : test d'anonymisation, et comparaison avec un classement humain (corrélation de Spearman) face à la baseline TF-IDF seule.

## Lancer le projet

**Prérequis :** Python 3.11 (ou Docker) et une clé API Gemini.

```bash
cp .env.example .env          # puis renseigner GEMINI_API_KEY et JWT_SECRET
pip install -r requirements.txt
uvicorn main:app --port 8000  # documentation interactive : http://localhost:8000/docs
```

**Évaluation (sans lancer l'API) :**

```bash
python eval/test_anonymizer.py eval/data/mon_cv.pdf
python eval/test_stabilite.py eval/data/mon_cv.pdf eval/data/offre.txt --runs 5
python eval/test_classement.py eval/data/offre.txt
```

Variable optionnelle `LLM_TEMPERATURE=0` pour comparer la stabilité à température nulle.

## Principaux endpoints

| Méthode | Endpoint | Rôle |
|---|---|---|
| POST | `/api/ats/parse-cv` | extraire le texte d'un CV (PDF/DOCX) |
| POST | `/api/ats/parse-offer-text` | structurer une offre avec le LLM |
| POST | `/api/ats/score` | scorer un candidat |
| POST | `/api/ats/score-bulk` | scorer plusieurs candidats |
| GET | `/api/ats/ranking/{job_offer_id}` | classement des candidats |
| POST | `/api/ats/feedback` | retour RH pour ajuster les poids |

## Stack

Python · FastAPI · Gemini 2.5 Flash · ChromaDB · Sentence-Transformers · scikit-learn · PyMuPDF · RabbitMQ · Docker · JWT

## Limites et perspectives

- **Non-déterminisme** du LLM → tester la température 0 et agréger plusieurs exécutions.
- **Poids fixés par jugement** (40/30/20/10), non calibrés sur des données réelles.
- **Évaluation sur peu de CV** → constituer un jeu de CV annotés.
- **Biais possibles** du LLM → tests contrefactuels (même CV, nom ou genre modifiés).
- CV scannés et mises en page complexes mal extraits → ajouter un OCR.

---

**Auteure :** Fatima Zahra SIDHOUM — élève ingénieure en Génie Informatique (spécialité IA), EHEIM Oujda · [LinkedIn](https://linkedin.com/in/FatimaZahraSidhoum)
