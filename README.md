# SiteLens AI - Backend API

FastAPI backend for construction oversight intelligence powered by Google Gemini.

## Project Structure

```
backend/
├── main.py                 # FastAPI app initialization and configuration
├── config.py              # Environment variables and settings
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── routers/              # API route handlers
│   ├── __init__.py
│   └── analyze.py        # /api/analyze endpoint
├── schemas/              # Pydantic models for request/response
│   ├── __init__.py
│   └── analyze.py        # Analysis schemas
├── services/             # Business logic layer
│   ├── __init__.py
│   └── gemini_service.py # Google Gemini API integration
└── utils/                # Helper utilities
    ├── __init__.py
    └── file_utils.py     # File handling and PDF extraction
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:
```
GEMINI_API_KEY=your_actual_api_key_here
```

Postgres (recommended) — optional

If you want to enable persistent storage, set a Postgres connection string in your `.env`:
```
# Example DATABASE_URL value
DATABASE_URL=postgres://user:password@localhost:5432/sitelens_db
```
If `DATABASE_URL` is not set, the app will run without a database but features that rely on persistence (projects, user auth, storing analyses) will be unavailable.

Get your Gemini API key from: https://makersuite.google.com/app/apikey

### 4. Run Development Server

```bash
uvicorn main:app --reload --port 8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoints

### POST /api/analyze

Analyze construction site files using Google Gemini AI.

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `files`: Multiple file uploads (PDFs, images, videos)
  - `project_name` (optional): Project identifier
  - `additional_context` (optional): Additional analysis context

**Response:**
```json
{
  "project_name": "Building A Construction",
  "summary": "Analysis complete. 3 observations documented for review.",
  "findings": [
    {
      "risk_type": "Safety Hazard",
      "risk_level": "high",
      "confidence": 0.95,
      "explanation": "Workers observed without proper fall protection",
      "location": "Image 1, Section 3",
      "recommendation": "Immediate safety briefing required"
    }
  ],
  "total_files_analyzed": 5,
  "analysis_timestamp": "2024-01-02T10:30:00"
}
```

## Frontend Integration

### Example: Calling from React

```typescript
const analyzeFiles = async (files: File[], projectName: string) => {
  const formData = new FormData();

  files.forEach(file => {
    formData.append('files', file);
  });

  formData.append('project_name', projectName);

  const response = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();
  return result;
};
```

## Development Notes

### Adding New Features

1. **New Endpoints**: Add routers in `routers/` directory
2. **Business Logic**: Implement in `services/` directory
3. **Data Models**: Define Pydantic schemas in `schemas/` directory
4. **Utilities**: Add helpers in `utils/` directory

### Error Handling

All endpoints include comprehensive error handling:
- 400: Bad Request (invalid files, missing required fields)
- 413: Request Entity Too Large (file size exceeded)
- 422: Unprocessable Entity (file processing failed)
- 500: Internal Server Error (unexpected errors)

### File Storage

- Uploaded files are temporarily stored in `./uploads/`
- Files are cleaned up after analysis completes
- Configure `UPLOAD_DIR` in `.env` to change location

## Production Deployment

### Environment Variables to Set

- `GEMINI_API_KEY`: Your production Gemini API key
- `CORS_ORIGINS`: Add your production frontend URLs
- `MAX_FILE_SIZE`: Adjust based on your needs
- `UPLOAD_DIR`: Set to appropriate storage location
- `SECRET_KEY`: Strong random secret for JWT signing

### Auth & RBAC

This project implements OAuth2 Password flow with JWTs and role-based access control.

Endpoints:
- POST `/api/v1/auth/signup` — create account (username, password, role: GOVERNMENT|CONTRACTOR)
- POST `/api/v1/auth/token` — username/password token exchange (returns bearer JWT)

RBAC rules (enforced by `require_role` dependency):
- GOVERNMENT → access `/revenue/*`, `/admin/*`, `/policy/*`
- CONTRACTOR → access `/projects/*`, `/resources/*`, `/research/*`

### Database & Alembic

This project uses `SQLModel` (async) + `asyncpg` for PostgreSQL. The Alembic `env.py` has been updated to use `SQLModel.metadata` and to load the DB URL from `app.core.config.settings` so autogeneration should work once you have imported your models in `app.models`.

Run migrations locally:

```bash
# Make sure DATABASE_URL is set in .env
alembic upgrade head
# To create a migration:
alembic revision --autogenerate -m "Added example model"
```

For Cloud Run, build the Docker image and deploy using `gcloud` or your CI system.

### Recommended: Add Rate Limiting

```bash
pip install slowapi
```

### Recommended: Add Authentication

Consider adding JWT authentication for production use.

## Troubleshooting

### Gemini API Errors

- Verify API key is correct in `.env`
- Check API quota limits
- Ensure model name is valid (e.g., `gemini-3`)

### Grounded Search

This code uses Google Custom Search (optional) to ground prompts for better factuality. Set `GOOGLE_API_KEY` and `GOOGLE_SEARCH_CX` in `.env` to enable web grounding.

### File Upload Issues

- Check `MAX_FILE_SIZE` setting
- Verify file MIME types in `ALLOWED_FILE_TYPES`
- Ensure `uploads/` directory has write permissions

### CORS Issues

- Add your frontend URL to `CORS_ORIGINS` in `.env`
- Clear browser cache if CORS headers are cached

## License

MIT
