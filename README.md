# Bluestar Sniper — standalone redesigned app

Self-contained deployment folder generated from the audited project root. It
contains the premium navy UI, the `bluestar` engine, the Streamlit theme config
and the recorded fixtures.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Offline demo (no token, no network):

```bash
BLUESTAR_FIXTURE_MODE=1 \
BLUESTAR_FIXED_NOW=2026-09-15T14:30:00+00:00 \
streamlit run app.py
```

## Secrets

Create `.streamlit/secrets.toml`:

```toml
OANDA_ACCESS_TOKEN = "your-practice-token"
OANDA_ENVIRONMENT = "practice"
```

The app is read-only: it only calls the OANDA candle endpoint and never creates,
modifies or closes orders. `practice` is the default.

## Streamlit Cloud

- Main file path: `app.py`
- Python: `3.12` (see `runtime.txt`)
- Add `OANDA_ACCESS_TOKEN` and `OANDA_ENVIRONMENT` under app secrets.
- Do not commit `.streamlit/secrets.toml`.

## Contents

- `app.py` — thin Streamlit entry point.
- `bluestar/` — engine, indicators, signals, scoring, OANDA client, UI/theme.
- `fixtures/` — recorded OANDA candles for offline demo and verification.
- `.streamlit/config.toml` — navy theme for native Streamlit widgets.
- `requirements.txt` — pinned runtime dependencies.
