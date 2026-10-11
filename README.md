# SAP Data Migration Cleaner

A full-stack web application that helps SAP consultants clean and validate data before importing it into SAP S/4HANA.

## Architecture

```
/backend      — FastAPI + PostgreSQL (Python)
/frontend     — Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend

```bash
cd backend

# Copy environment file and configure
cp .env.example .env
# Edit .env: set DATABASE_URL and GEMINI_API_KEY

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate  (Linux/Mac)

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at: http://localhost:3000

### PostgreSQL Setup

```sql
CREATE DATABASE sap_cleaner;
CREATE USER sap_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE sap_cleaner TO sap_user;
```

Then set `DATABASE_URL=postgresql+asyncpg://sap_user:your_password@localhost:5432/sap_cleaner` in `.env`.

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@localhost/sap_cleaner` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8000` |

## Features

- **Multi-format ingestion**: .xlsx, .xls, .csv, .json, paste
- **15+ anomaly types**: duplicates, format errors, missing required fields, SAP-specific rules
- **LLM-powered suggestions**: Gemini 2.0 Flash via `llm_service.py` (swappable to Ollama)
- **Interactive correction UI**: accept / reject / manual edit per anomaly
- **Bulk accept high-confidence**: auto-accept all corrections ≥ 80% confidence
- **Export**: clean CSV, clean XLSX, PDF validation report
- **Session management**: PostgreSQL-backed sessions with history

## LLM Provider Swap (Gemini → Ollama)

Edit only `backend/app/core/llm_service.py`:
1. Replace `import google.generativeai as genai` with your Ollama client
2. Replace `self._model = genai.GenerativeModel(...)` initialization
3. Replace the body of `_call_llm()` with an Ollama HTTP call

No other files need to change.

## SAP Validation Rules

Configurable in `backend/app/core/validator.py`:
- `SAP_REQUIRED_FIELDS` — required vendor fields
- `SAP_PAYMENT_TERMS` — valid payment term codes
- `SAP_ACCOUNT_GROUPS` — valid account group codes
- `SAP_FIELD_MAX_LENGTHS` — per-field character limits
- `SAP_FORBIDDEN_CHARS` — characters rejected by SAP
