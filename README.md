# BLUESTAR SNIPER V18

Scanner multi-timeframes OANDA v20 (practice) avec interface Streamlit.

## Structure

```
app.py                          interface Streamlit
bluestar/                       moteur d'analyse
  config.py                     instruments, seuils, poids de score
  clock.py                      horloge injectable, killzones
  data.py                       transport OANDA, retry/backoff, rate limit
  engine.py                     pipeline complet par instrument
  analysis.py                   zones, ADR, midnight open
  signals.py                    biais daily, HMA, MTF, FVG
  scoring.py                    calcul du score /103 et du grade
  ui_css.py                     theme navy premium et tokens de couleur
  indicators/                   ADX, ATR, RSI, HMA, ZLEMA
.streamlit/config.toml          theme Streamlit (fond navy)
requirements.txt                dependances epinglees
env.example                     modele de credentials
```

## Deploiement Streamlit Cloud

1. Pousser ce dossier a la racine du depot (app.py doit etre a la racine).
2. Manage app -> Settings -> Python version : 3.10 a 3.13.
3. Manage app -> Settings -> Secrets :

```toml
OANDA_ACCESS_TOKEN = "ton-token-65-caracteres"
OANDA_ENVIRONMENT = "practice"
```

Le token n'est jamais affiche, journalise ou inclus dans une erreur.
Ne jamais committer de fichier .env (deja exclu par .gitignore).

## Regles de qualite

- Aucun fichier de test, d'audit ou d'outillage dans ce depot : application uniquement.
- Aucun module duplique a la racine : tout le code vit dans bluestar/.
- Les seuils de scoring sont implementes dans scoring.py ; les tables de config.py
  doivent rester alignees (un test de coherence est recommande avant toute modification).
