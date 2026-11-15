# Bluestar Sniper v17

Scanner multi-timeframe (HMA 20 M15 · biais daily · zones ICT · force devise · ADX) sur OANDA,
**lecture seule** (uniquement `GET /v3/instruments/{instrument}/candles`). Interface Streamlit.

## Lancer

```bash
pip install -r requirements.txt
export OANDA_ACCESS_TOKEN="..."            # ou .streamlit/secrets.toml
export OANDA_ENVIRONMENT="practice"        # practice (défaut) | live
streamlit run app.py
```

`.streamlit/secrets.toml` :

```toml
OANDA_ACCESS_TOKEN = "votre-token"
OANDA_ENVIRONMENT = "practice"
```

## Tests et qualité

```bash
pip install -r requirements-dev.txt
pytest                       # 111 tests : indicateurs, biais, score, moteur, OANDA, UI Streamlit, hygiène
```

La suite vérifie aussi que le code supprimé ne revient pas (FVG, DI+/DI−), que `pyflakes` est propre
et qu'il n'y a pas de code mort (`vulture`).

## Architecture

| Module | Rôle |
|---|---|
| `config.py` | **Tous** les seuils, poids, timeframes, univers. Rien d'autre ne code de nombre magique. |
| `indicators.py` | WMA/HMA, ATR, **ADX (courbe seule)**, RSI, pivots, ADR. Purs. |
| `levels.py` | Midnight open, Weekly open (depuis le M15), zone Premium/Discount. |
| `signals.py` | Tendance TF (définition unique), MTF, biais daily (7 votes), force devise, ADX multi-TF, état HMA. |
| `scoring.py` | Score /100 traçable, renormalisé si la force devise est indisponible. |
| `engine.py` | `fetch_universe` (1 requête par actif×TF, sans doublon) → `analyze_asset` (pur) → `run_scan`. |
| `data/oanda.py` | Client OANDA : sessions réutilisées par thread, retries, rate-limit, jamais de secret dans les erreurs. |
| `ui/` | `app.py` (câblage), `render.py` (HTML pur + filtres), `theme.py` (CSS). |

## Règles métier

**Signal.** HMA 20 sur M15, prix du bon côté de la HMA.
- *Flip* : la HMA a changé de couleur il y a ≤ 20 bougies.
- *Tendance* (`CONTINUATION_ENABLED`) : pas de flip récent, mais biais daily **aligné** et zone **favorable**.
  Le Trigger vaut 0 → score max 70.

**Score /100** : Trigger 30 · MTF 25 · Zone 15 · Biais 10 · Force devise 10 · ADX 10,
malus ADR > 70 % (−5) et contre-biais (−20). Grades : A+ ≥ 85 · A ≥ 70 · B+ ≥ 55 · B ≥ 40.

**Biais daily** : 7 votes (structure ±2, EMA 21/50, Weekly Open, clôture J-1, pente EMA50, pente HMA20).
Directionnel à ≥ 3 votes et majorité stricte, STRONG à ≥ 5. Une structure cassée interdit seulement de
continuer *dans le sens cassé* ; elle n'annule plus un retournement confirmé.

**ADX** : uniquement la courbe (force de tendance, sans direction). Un segment s'allume si l'ADX d'un
timeframe (H4, H1, M15) dépasse `ADX_TREND_MIN`.

## Ce qui est volontairement observable

Survol (tooltips) : détail des votes du biais, détail du score, tendance par timeframe, référence de zone.
Mode 🐛 Debug : motif de rejet de chaque actif + tableau « pourquoi ce biais / ce score ».
Les résultats persistent : changer un filtre ne relance pas de scan.

## Limites connues

- Jours fériés non modélisés (un marché fermé hors week-end apparaît « DONNÉES PÉRIMÉES »).
- Les seuils de grade sont à recalibrer sur vos scans réels (journaliser le Debug quelques jours).
