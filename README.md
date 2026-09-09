# learnhub-admin

Streamlit admin dashboard for LearnHub, backed by Supabase (service-role key,
server-side only).

## Run locally

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Credentials: env vars OR .streamlit/secrets.toml (copy secrets.toml.example)
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

- Main file: `app.py`
- Python: 3.10–3.12
- Secrets: paste `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`