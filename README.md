# SEO + AEO Business Impact Simulator

A Streamlit app to simulate SEO, AEO/GEO readiness and business impact without using AI tokens.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What it does

- Scores current SEO, content, authority and AEO/GEO readiness.
- Lets you select improvement actions.
- Projects visibility lift.
- Translates the projected lift into sessions, leads, opportunities, clients and revenue.
- Exports the simulation to CSV.

## Why it does not consume tokens

The simulator uses fixed scoring rules in Python. AI can be added later as an optional button to generate a written recommendation only when needed.
