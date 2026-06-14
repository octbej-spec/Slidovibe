# Radar Ingénierie STM - Sondage interactif d'équipe

**Radar Ingénierie STM** est une application web interactive construite avec **Streamlit** et **SQLite**, conçue pour animer des sondages en direct lors des rencontres d'équipe d'ingénierie de la STM.

L'application permet aux participants de soumettre des réponses anonymes à des questions ouvertes en temps réel, tandis que l'animateur dispose d'un tableau de bord sécurisé pour contrôler la question active globale, observer les statistiques, générer des nuages de mots dynamiques et exporter les résultats.

---

## Fonctionnalités

### 🙋‍♂️ Mode Participant
* **Accès simple et sans connexion** (aucune configuration requise sur mobile ou ordinateur).
* **Question active synchronisée** en temps réel avec le choix de l'animateur.
* **Validation des entrées** : empêche les réponses vides et nettoie les espaces superflus.
* **Sécurité anti-double clic** : empêche les soumissions accidentelles identiques successives.

### 🎙️ Mode Animateur
* **Contrôle de la question active** globale diffusée à tous les participants.
* **Statistiques en direct** : nombre total de réponses récoltées par question.
* **Visualisation interactive** :
  * Nuage de mots-clés généré dynamiquement en bleu STM (exclut les mots de liaison courants en français).
  * Liste du Top 5 des mots les plus fréquemment soumis.
  * Tableau brut de toutes les réponses reçues.
* **Exportation des données** en un clic vers des formats exploitables :
  * **CSV** (encodage UTF-8-sig compatible avec Excel français).
  * **Excel (XLSX)** stylisé avec colonnes auto-ajustées.
* **Sécurisation par mot de passe** configurable via secrets ou variables d'environnement.
* **Option de réinitialisation** sécurisée par double validation (case à cocher + bouton).

---

## Structure du projet

```text
radar-ingenierie-stm/
│
├── app.py                  # Point d'entrée de l'application Streamlit
├── requirements.txt        # Dépendances Python requises
├── README.md               # Guide d'utilisation et de déploiement
├── .gitignore              # Règles d'exclusion Git
│
├── data/
│   └── sondage.db          # Base de données SQLite locale (générée automatiquement)
│
├── src/
│   ├── database.py         # Gestion de la DB, des requêtes SQL et de la prévention des doublons
│   ├── questions.py        # Fichier de définition des questions du sondage
│   ├── wordcloud_utils.py  # Fonctions pour générer le nuage de mots et filtrer les stopwords
│   └── export_utils.py     # Fonctions d'exportation vers CSV et Excel
│
└── .streamlit/
    └── config.toml         # Thème visuel personnalisé STM (couleurs, polices)
```

---

## Installation et démarrage local

### 1. Prérequis
Assurez-vous d'avoir Python 3.8 ou une version ultérieure installée sur votre machine.

### 2. Cloner le projet et installer les dépendances
Ouvrez votre terminal dans le dossier du projet et exécutez la commande suivante pour installer les packages requis :

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application
Pour exécuter l'application localement, lancez :

```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse locale : `http://localhost:8501`.

---

## Tester l'application sur Téléphone (Réseau local)

Pour simuler l'utilisation par vos collaborateurs sur leurs téléphones lors de votre réunion :
1. Connectez votre ordinateur et votre téléphone sur le **même réseau Wi-Fi**.
2. Récupérez l'**adresse IP locale** de votre ordinateur (Network URL affichée dans le terminal lors du lancement de Streamlit, par exemple `http://192.168.1.50:8501`).
3. Saisissez cette adresse IP dans le navigateur internet de votre téléphone.

---

## Configuration de la sécurité (Mode Animateur)

Par défaut, si aucune configuration de sécurité n'est détectée, un avertissement s'affiche et l'accès au mode animateur reste libre (pratique en phase de développement).

Pour sécuriser l'accès en production :

### Option A : Streamlit Secrets (Recommandé pour Streamlit Cloud)
Dans votre projet local, créez un fichier `.streamlit/secrets.toml` (déjà dans le `.gitignore`) et ajoutez-y :
```toml
ADMIN_PASSWORD = "votre_mot_de_passe_secret"
```

### Option B : Variable d'environnement (Recommandé pour serveurs internes/Docker)
Définissez la variable d'environnement `ADMIN_PASSWORD` avant de lancer Streamlit :

* **Sur Windows (PowerShell) :**
  ```powershell
  $env:ADMIN_PASSWORD="votre_mot_de_passe_secret"
  streamlit run app.py
  ```
* **Sur Linux / macOS :**
  ```bash
  export ADMIN_PASSWORD="votre_mot_de_passe_secret"
  streamlit run app.py
  ```

---

## Déploiement

### Déploiement sur Streamlit Community Cloud
1. Déposez votre code sur un dépôt **GitHub** public ou privé (assurez-vous que `data/` et `.streamlit/secrets.toml` soient exclus par le `.gitignore`).
2. Connectez-vous sur [Streamlit Community Cloud](https://share.streamlit.io/).
3. Cliquez sur **New app** et sélectionnez votre dépôt.
4. Dans les paramètres avancés (**Advanced settings**), configurez le mot de passe dans la section **Secrets** :
   ```toml
   ADMIN_PASSWORD = "votre_mot_de_passe_secret"
   ```
5. Cliquez sur **Deploy**. L'application est en ligne !

### Déploiement sur un serveur interne (STM)
Vous pouvez héberger l'application sur un serveur Windows ou Linux interne à la STM. Il suffit d'installer Python, de cloner le dépôt, d'installer les dépendances et de faire tourner Streamlit en tâche de fond (par exemple avec `nohup`, un service systemd, ou via un conteneur Docker).

---

## Exportation des résultats
À la fin de la séance, accédez au **Mode Animateur**, entrez votre mot de passe, allez dans l'onglet **⚙️ Exporter & Réinitialiser** :
* Cliquez sur **Exporter en CSV** pour télécharger un fichier contenant toutes les réponses séparées par des virgules.
* Cliquez sur **Exporter en Excel** pour obtenir un fichier Excel formaté avec une présentation soignée des en-têtes en bleu STM et l'ajustement automatique de la largeur des colonnes.
