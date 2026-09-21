# NSDC AI Assistant

A lightweight FastAPI assistant for NSDC and Skill India information. Responses
are grounded in the local JSON knowledge base before OpenRouter is called.

## Features

- FastAPI chat and health endpoints
- Normalized, scored keyword retrieval with the top three records
- Source, page, and category attribution
- Safe fallback responses for missing configuration, timeouts, network errors,
  and malformed knowledge data
- Browser-session history, quick actions, and typing indicator
- Pytest coverage for retrieval, loading, API health, and malformed data

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` with configuration supplied by your deployment environment:

```dotenv
OPENROUTER_API_KEY=your-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=your-model-id
OPENROUTER_TIMEOUT_SECONDS=15
```

The API remains available without an OpenRouter key, and returns a temporary
service message for matched questions instead of exposing configuration errors.

## Run

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in a browser.

## Test

```bash
pytest -q
```