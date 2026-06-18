# 📚 Bibliomind — Moteur de Recommandation de Livres par IA

Une application web full-stack de recommandation de livres alimentée par l'IA, construite avec :

- **Python + Flask** — Framework web
- **MySQL** — Base de données relationnelle (utilisateurs, livres, notes, favoris, liste de lecture)
- **Scikit-learn** — Moteur de recommandation hybride
  - `TfidfVectorizer` → Filtrage basé sur le contenu
  - `TruncatedSVD` → Filtrage collaboratif (Factorisation matricielle)
  - Reclassement par moyenne bayésienne
  - Extraction automatique de tags pour les explications de recommandations

---

## 🏗️ Structure du projet
book-recommender/

│

├── run.py                    # Point d'entrée Flask

├── requirements.txt          # Dépendances Python

├── .env.example              # Modèle de variables d'environnement

│

├── config/

│   └── config.py             # Configuration Flask

│

├── app/

│   ├── init.py           # Fabrique d'application

│   ├── models.py             # Modèles SQLAlchemy (User, Book, Rating, Favorite, ReadingList)

│   ├── routes.py             # Toutes les routes Flask + endpoints API REST

│   └── templates/

│       ├── base.html             # Mise en page de base (nav, footer, styles globaux)

│       ├── index.html            # Page d'accueil

│       ├── books.html            # Catalogue avec recherche, filtre par genre et tri

│       ├── book_detail.html      # Page livre avec recommandations IA similaires

│       ├── dashboard.html        # Tableau de bord avec recommandations IA

│       ├── recommendations.html  # Page complète des recommandations IA

│       ├── profile.html          # Profil utilisateur & statistiques de lecture

│       ├── login.html

│       └── register.html

│

├── ml/

│   ├── init.py

│   ├── recommender.py        # 🧠 Moteur IA (Contenu + Collaboratif + Hybride)

│   ├── embeddings.py         # Extraction de tags & explications des recommandations

│   ├── scorer.py             # Score bayésien + score de popularité

│   └── saved_models/         # Modèles entraînés sérialisés (créé automatiquement)

│

└── database/

└── seed.py               # Peuplement de la BDD + entraînement des modèles IA

---

## ⚙️ Installation dans VS Code

### 1. Prérequis
- Python 3.12(ideal)
- Serveur MySQL en cours d'exécution en local

### 2. Créer un environnement virtuel
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
```

Modifiez le fichier `.env` avec vos identifiants — **les deux variables sont obligatoires**, l'application refusera de démarrer si l'une d'elles est absente :
SECRET_KEY=une-chaine-aleatoire-longue

DATABASE_URL=mysql+pymysql://root:VOTRE_MOT_DE_PASSE@localhost/book_recommender

### 5. Créer la base de données MySQL
```sql
-- Dans MySQL Workbench ou le CLI :
CREATE DATABASE book_recommender CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. Peupler la base de données + entraîner les modèles IA
```bash
python database/seed.py
```
Ce script va :
- Créer toutes les tables
- Insérer 24 livres répartis sur 9 genres (Fantasy, Sci-Fi, Mystère, Horreur, Romance, Historique, Documentaire, Business, Développement personnel)
- Créer 5 utilisateurs de démonstration avec des notes réalistes
- **Entraîner les modèles de recommandation IA**

### 7. Lancer l'application
```bash
python run.py
```

Ouvrez http://localhost:5000

---

## 🔑 Compte de démonstration
Email :      alice@example.com

Mot de passe : password123
Autres utilisateurs : `bob`, `charlie`, `diana`, `eve` (même mot de passe)

---

## 🧠 Fonctionnement de l'IA

### Filtrage basé sur le contenu
Utilise `TfidfVectorizer` pour convertir les métadonnées des livres (titre, auteur, genre, description)
en vecteurs TF-IDF. La similarité cosinus entre vecteurs permet de trouver des livres similaires à ceux appréciés par l'utilisateur.

### Filtrage collaboratif
Utilise `TruncatedSVD` (factorisation matricielle) sur la matrice notes utilisateur-livre pour
décomposer des facteurs latents et prédire les préférences de l'utilisateur pour les livres non lus.

### Recommandeur hybride
```python
score_final = 0.6 × score_collaboratif + 0.4 × score_contenu
```

### Reclassement bayésien
Les scores sont reclassés à l'aide d'une moyenne bayésienne pour éviter qu'un livre avec une seule note de 5 étoiles dépasse un livre avec des milliers de notes :
score_bayésien = (C × moyenne_globale + n × note_moyenne) / (C + n)
La popularité (nombre de notes normalisé en logarithme) est également intégrée dans le score final.

### Explications des recommandations
Des tags sont extraits automatiquement pour chaque livre via TF-IDF sur les descriptions. Lors d'une recommandation, les tags communs entre les livres appréciés et le livre candidat sont présentés sous forme de raison lisible (ex. : *« Thèmes partagés : Fantasy Sombre, Magie Ancienne »*).

Les modèles sont **réentraînés automatiquement** dans un thread en arrière-plan à chaque nouvelle note soumise par un utilisateur.
Les résultats sont **mis en cache pendant 5 minutes** par utilisateur pour des réponses rapides.

---

## 🌐 Routes & Endpoints API

### Pages
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Page d'accueil |
| GET | `/books` | Catalogue (filtre genre, recherche, tri) |
| GET | `/books/<id>` | Détail d'un livre + livres similaires IA |
| GET | `/dashboard` | Tableau de bord + recommandations IA |
| GET | `/recommendations` | Page complète des recommandations IA |
| GET | `/profile` | Profil utilisateur, statistiques & liste de lecture |

### API REST
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/rate` | Noter un livre `{book_id, score, review}` |
| POST | `/api/favorite` | Ajouter/retirer des favoris `{book_id}` |
| POST | `/api/reading-list` | Gérer la liste de lecture `{book_id, status}` |
| GET | `/api/recommendations` | Recommandations IA (JSON) |
| GET | `/api/search?q=` | Recherche de livres en temps réel (JSON) |
| GET | `/api/books/<id>/tags` | Tags générés automatiquement pour un livre (JSON) |

#### Statuts de la liste de lecture
`want_to_read` · `reading` · `finished` · `remove`

---

## 🛠️ Extensions VS Code recommandées
- Python (Microsoft)
- Flask Snippets
- SQLTools + SQLTools MySQL/MariaDB
- Thunder Client (test d'API)