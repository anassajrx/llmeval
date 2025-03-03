# LLM Evaluation System

Un système complet d'évaluation des modèles de langage (LLM) basé sur des QCM générés automatiquement, spécialisé pour le domaine juridique.

## 🌟 Caractéristiques

- **Traitement de Documents**
  - Extraction de texte à partir de PDF
  - Découpage intelligent en chunks
  - Génération d'embeddings avec Gemini

- **Génération de QCM**
  - Questions contextualisées
  - Multiple critères d'évaluation
  - Niveaux de difficulté variables

- **Évaluation Avancée**
  - Tests de biais
  - Vérification d'intégrité
  - Conformité légale
  - Analyse de cohérence

- **Rapports Détaillés**
  - Visualisations interactives
  - Métriques avancées
  - Exportation multi-format

## 📋 Prérequis

- Python 3.8+
- Base de données PostgreSQL avec extension pgvector
- Clé API Gemini
- Environnement virtuel Python (recommandé)

## 🚀 Installation

1. Cloner le repository :
```bash
git clone https://github.com/votre-username/llm-evaluation-system.git
cd llm-evaluation-system
```

2. Créer et activer l'environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/MacOS
# ou
venv\Scripts\activate  # Sur Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les clés API :
- Créer un fichier `.env.apikey` dans `AI_API/API_Calls/GeminiProAPI/settings/`
- Créer un fichier `.env.apikey` dans `AI_API/API_Calls/PostgresURL/settings/`

## 📊 Utilisation

1. Placer les documents PDF à analyser dans le dossier `data/input/`

2. Exécuter le système :
```bash
python main.py
```

3. Consulter les résultats dans le dossier `data/output/`

## 📁 Structure du Projet

```
llm_evaluation_system/
├── config/                 # Configuration
├── core/                   # Composants principaux
├── generators/             # Générateurs (QCM, rapports)
├── evaluators/            # Systèmes d'évaluation
├── utils/                 # Utilitaires
├── tests/                 # Tests unitaires
└── data/                  # Données
    ├── input/             # Documents d'entrée
    └── output/            # Résultats et rapports
```

## 🔍 Détails Techniques

### Traitement des Documents
- Utilisation de PyMuPDF pour l'extraction de texte
- Chunking avec chevauchement pour maintenir le contexte
- Embeddings via l'API Gemini

### Génération de QCM
- Questions basées sur le contexte extrait
- 5 critères d'évaluation principaux
- 3 niveaux de difficulté par critère

### Évaluation
- Tests de résistance aux biais
- Vérification de cohérence
- Analyse de conformité légale
- Métriques de performance détaillées

## 📈 Métriques d'Évaluation

- Score global
- Scores par critère
- Taux de réussite
- Résistance aux biais
- Intégrité des réponses
- Conformité légale
- Cohérence logique

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👥 Auteurs

- Votre Nom (@votre-username)

## 📧 Contact

Pour toute question ou suggestion, veuillez ouvrir une issue dans le repository GitHub.

## 🙏 Remerciements

- Anthropic pour l'API Claude
- Google pour l'API Gemini
- La communauté open source pour les différentes bibliothèques utilisées
```

Ceci termine la structure de base du projet. Je peux maintenant :
1. Créer un script d'installation
2. Ajouter des tests unitaires
3. Améliorer la documentation
4. Ajouter des exemples d'utilisation

Que souhaitez-vous que je fasse ensuite ?