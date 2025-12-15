## Chat RAG – Cabinet d'avocats

Application Streamlit multipage (Chat + Documents) avec pipeline RAG strict. Réponses uniquement basées sur les documents uploadés. Vector store Chroma persistant, embeddings et LLM via API OpenAI.

### Fonctionnalités
- Upload multiples `.txt`, `.csv`, `.html` avec nettoyage, chunking, embeddings et upsert dans Chroma
- Suppression par document (supprime tous les chunks liés)
- Chat avec historique multi-conversations (persisté en SQLite) et affichage des sources utilisées
- Garde-fous : refus hors corpus, seuil de similarité, détection basique d'injection
- Persistance : index/chunks sur disque (`app/data/chroma/`), registre des documents JSON, conversations dans `app/data/conversations.db`

### Structure
- app/Home.py : page d'accueil
- app/pages/1_Chat.py : interface chat + sources
- app/pages/2_Documents.py : upload, liste, suppression
- app/core : settings, logging, erreurs, sécurité, utils
- app/rag : store Chroma, ingestion, retrieval, prompts, génération
- app/loaders : loaders spécifiques txt/csv/html
- app/ui : state session, composants UI
- scripts/reset_index.py : reset complet (dev)
- tests : nettoyage, chunking, garde-fous RAG

### Prérequis
- Python >= 3.11
- Clé OpenAI via variable d'environnement `OPENAI_API_KEY`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
Copiez `.env.example` vers `.env` et renseignez `OPENAI_API_KEY`.

### Lancement
```bash
streamlit run app/Home.py
```
Page Documents : uploadez des fichiers, vérifiez le compteur de chunks/documents. Page Chat : posez vos questions, l'app répond uniquement si des sources pertinentes sont trouvées, sinon message "Je ne sais pas d'après les documents fournis." Les sources sont listées dans un expander.

### Stockage des conversations
- Local uniquement : SQLite `app/data/conversations.db` (créé au lancement), pas de télémetrie externe.
- Chaque message est inséré en base; les conversations sont rechargées au démarrage pour retrouver l'historique.
- Pour repartir de zéro : supprimez `app/data/conversations.db` (optionnel, l'app le recréera).

### Tests
```bash
pytest
```

### Lint / Format
Ruff est le linter (peut aussi autofixer), Black est le formateur. Exécutez Ruff avant Black.
```bash
ruff check .
ruff check . --fix  # optionnel pour corriger automatiquement
black .
```

### Garde-fous RAG
- Pas de réponse sans contexte pertinent : fallback systématique
- Seuil de distance (cosine) configurable (`max_distance`)
- Refus simple de tentatives d'injection dans la question
- Pas de logging de contenu sensible (logs techniques uniquement)

### Reset index (dev)
```bash
python scripts/reset_index.py
```

### Limitations connues
- Tests unitaires évitent l'appel réseau (pas de test e2e LLM)
- Chunking approximatif (caractères) au lieu de tokens
- CSV tronqué à 200 lignes pour éviter la verbosité
