# AGENTS.md — Streamlit RAG Chat (Cabinet d’avocats) PoC

Ce fichier décrit l’architecture cible, les conventions, et les bonnes pratiques pour construire un PoC **propre, maintenable et sécurisé** : une app **Streamlit** à 2 pages (Chat + Documents) avec un pipeline **RAG** (documents uploadés, nettoyés, chunkés, vectorisés, recherchés) et un LLM appelé via **API**.

---

## 1) Objectif et contraintes non négociables

### 1.1 Objectif
- Fournir un chatbot interne permettant de répondre **uniquement** à partir des documents uploadés (corpus interne anonymisé).
- Mettre à disposition une page de gestion documentaire : upload / suppression / indexation automatique.

### 1.2 Contraintes
- **Aucune génération hors corpus** : si les documents ne contiennent pas l’info, le bot doit le dire explicitement.
- **Confidentialité** : pas de logs contenant des contenus sensibles, pas d’exfiltration involontaire via traces / exceptions.
- **Traçabilité** : réponses accompagnées de sources (document + extrait + score/position), au minimum en “expander”.
- **Robustesse** : gestion des erreurs (fichiers invalides, index absent, clé API manquante, etc.).

---

## 2) Stack recommandée (PoC stable)

### 2.1 Runtime
- Python 3.12+
- Streamlit multipage

### 2.2 RAG
- Vector store : **Chroma** (persistant sur disque) ou FAISS (persistant via fichiers).
- Embeddings : via API (OpenAI `text-embedding-3-small` ou équivalent) ou alternative (Mistral/Claude embeddings si dispo).
- Chunking : basé sur taille + chevauchement (ex: 800–1200 tokens, overlap 150–200), avec séparation par paragraphes quand possible.

### 2.3 LLM
- LLM via API (OpenAI / Mistral / Claude).
- Réponses contrôlées via un prompt strict et validation “no answer if no evidence”.

---

## 3) Architecture projet

### 3.1 Arborescence recommandée

.
├── app/
│   ├── Home.py                       # (optionnel) page d’accueil / routing
│   ├── pages/
│   │   ├── 1_Chat.py                 # page chatbot
│   │   └── 2_Documents.py            # page gestion docs
│   ├── ui/
│   │   ├── components.py             # petits composants UI (sources, badges, etc.)
│   │   └── state.py                  # gestion session_state (conversations, sélection, etc.)
│   ├── core/
│   │   ├── settings.py               # lecture env, constantes, chemins
│   │   ├── logging.py                # logging safe (sans contenu sensible)
│   │   ├── security.py               # garde-fous (PII redaction optionnelle, anti prompt injection)
│   │   ├── errors.py                 # exceptions custom + mapping user-friendly
│   │   └── utils.py                  # helpers génériques
│   ├── rag/
│   │   ├── store.py                  # init vectordb (Chroma/FAISS), persistence
│   │   ├── ingest.py                 # pipeline ingestion (load -> clean -> chunk -> embed -> upsert)
│   │   ├── retriever.py              # retrieval (k, filters), formatage résultats
│   │   ├── prompts.py                # prompts system/user, templates
│   │   └── answer.py                 # génération contrôlée + citations + fallback
│   ├── loaders/
│   │   ├── txt_loader.py
│   │   ├── csv_loader.py
│   │   └── html_loader.py
│   └── data/
│       ├── raw/                      # fichiers uploadés (si on les conserve)
│       └── chroma/                   # persistance vectordb
├── tests/
│   ├── test_cleaning.py
│   ├── test_chunking.py
│   └── test_retrieval_guardrails.py
├── scripts/
│   └── reset_index.py                # utilitaire pour reset propre du vectordb (dev)
├── README.md
├── AGENTS.md
├── .env.example
├── .gitignore
├── pyproject.toml                    # ou requirements.txt
└── Makefile                          # (optionnel) raccourcis

### 3.2 Principes
- **Séparation UI / Core / RAG** : Streamlit ne doit pas contenir la logique métier.
- **Fonctions pures** et testables : nettoyage, chunking, scoring, etc.
- **État** : `st.session_state` centralisé (ui/state.py) pour conversations et sélection.
- **Persistant** : index vecteur sur disque (pas uniquement mémoire), pour relancer l’app sans perdre l’index.

---

## 4) Contrat fonctionnel des pages

### 4.1 Page “Documents”
- Upload `.txt`, `.csv`, `.html` (plus tard PDF si besoin, mais hors scope).
- Pour chaque upload :
  1) Validation extension/taille
  2) Lecture via loader dédié
  3) Nettoyage (normalisation)
  4) Chunking
  5) Embeddings + upsert dans vectordb
  6) Feedback utilisateur (nb chunks, doc_id)
- Suppression :
  - Supprimer par `doc_id` (et supprimer chunks associés dans vectordb)
  - Optionnel : supprimer le fichier dans `data/raw/`

UI attendue :
- Liste des documents indexés (doc_id, filename, date, nb chunks)
- Bouton “Supprimer”
- Zone d’upload multiple

### 4.2 Page “Chat”
- Interface type chat (`st.chat_input`, `st.chat_message`)
- À chaque question :
  1) Retrieval top-k chunks
  2) Si aucun chunk au-dessus d’un seuil : réponse “Je ne sais pas d’après les documents fournis.”
  3) Sinon : génération LLM **avec obligation de citer les sources**
- Bonus :
  - Historique multi-conversations (liste à gauche : “Nouvelle conversation”, conversations existantes)
  - Stockage local simple : JSON dans `data/` ou sqlite (PoC) — sans contenu sensible dans logs

---

## 5) Pipeline données : nettoyage & chunking

### 5.1 Nettoyage minimal (simple et efficace)
- Uniformiser encodage (UTF-8)
- Normaliser espaces et sauts de ligne
- Supprimer artefacts HTML (tags, scripts, styles) pour `.html`
- CSV :
  - convertir en texte lisible : en-têtes + lignes, ou bien “col: value”
  - limiter la verbosité (ex: max lignes, ou échantillonnage) si très volumineux
- Déduplication légère :
  - supprimer lignes vides répétées
  - optionnel : hash par chunk pour éviter double index

### 5.2 Chunking
- Chunk par taille (caractères ou tokens) + overlap
- Conserver métadonnées :
  - `doc_id`, `filename`, `source_type`, `chunk_index`, `char_start`, `char_end`, `created_at`
- Objectif : chunks autoportants (titre/section si détectable)

---

## 6) Sécurité & garde-fous (PoC mais sérieux)

### 6.1 Clés API
- Jamais en dur.
- `.env` local + `.env.example` dans repo.
- Lire via `os.environ` (core/settings.py).

### 6.2 Prompt injection / data exfiltration
- Le système doit :
  - ignorer les instructions présentes dans les documents (“ignore previous…”)
  - refuser de répondre si la question demande du contenu non présent
- Ajouter un bloc “Règles” dans le prompt system.

### 6.3 Logging “safe”
- Logger des événements techniques (upload ok, nb chunks, erreurs) mais **pas** le contenu des documents ni le texte complet des questions/réponses.
- En cas d’erreur, afficher un message utilisateur clair + trace technique minimale.

---

## 7) Qualité : tests, lint, format

### 7.1 Tests minimaux (rapides)
- `test_cleaning.py` : HTML stripping, normalisation espaces
- `test_chunking.py` : overlap, métadonnées, taille
- `test_retrieval_guardrails.py` : “pas de sources => pas de réponse”

### 7.2 Outils recommandés
- `ruff` (lint + format) ou `black` + `isort`
- `pytest`

---

## 8) Convention de code

- Typage : annotations Python (`from __future__ import annotations`) + `typing`
- Fonctions courtes, docstrings simples.
- Exceptions custom : `AppError`, `IngestError`, `VectorStoreError`, etc.
- Pas de logique RAG dans les pages Streamlit : uniquement orchestration + rendu.

---

## 9) Documentation “ce que l’on fait” (à maintenir)

### 9.1 Decision log
Créer/maintenir une section dans README (ou `docs/decisions.md`) :
- Pourquoi Chroma vs FAISS
- Paramètres chunking
- Seuil de similarité / fallback
- Format des sources (citations)

### 9.2 Checklist livraison
- [ ] Upload / delete fonctionne
- [ ] Index persistant
- [ ] Chat répond uniquement si sources trouvées
- [ ] Sources affichées
- [ ] Gestion clé API + .env.example
- [ ] README complet (setup + run + limitations)
- [ ] Tests minimaux passent

---

## 10) Définition du “Done” (PoC)
- App Streamlit 2 pages opérationnelle
- Corpus indexé et consultable par RAG
- Réponses avec citations + refus hors corpus
- Code modulaire, lisible, testable
- README clair