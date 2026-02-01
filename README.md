# Document Translator (Vision-LLM) MVP

Minimal working skeleton for Document Translator MVP.

## Project Structure

```
.
├── /apps/
│   ├── /api/          # FastAPI backend (Python 3.11)
│   └── /web/          # Next.js frontend (TypeScript)
├── /infra/            # Docker Compose and dev scripts
├── /docs/             # Documentation
├── /data/             # Storage directory (gitignored)
├── .env.example
├── Makefile
└── README.md
```

## Prerequisites

- Python 3.11
- Node.js 18+
- Docker & Docker Compose
- pnpm (preferred) or npm

## Quick Start

### 1. Install dependencies

```bash
make install
```

### 2. Start Redis

```bash
make redis-up
```

### 3. Start Backend (API)

In terminal 1:
```bash
make api-dev
```

API will be available at: http://localhost:8000

### 4. Start Frontend (Web)

In terminal 2:
```bash
make web-dev
```

Web app will be available at: http://localhost:3000

## Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make redis-up` | Start Redis container |
| `make redis-down` | Stop Redis container |
| `make api-dev` | Start FastAPI development server |
| `make web-dev` | Start Next.js development server |
| `make dev` | Start both API and Web in parallel |
| `make lint` | Run linters on all code |
| `make format` | Format all code |

## Ports

- **API**: http://localhost:8000
- **Web**: http://localhost:3000
- **Redis**: localhost:6379

## Health Check

Visit http://localhost:3000 and click "Check API" button to test the connection to the backend.

## Testing the Upload API

### Upload a PDF file:
```bash
curl -X POST http://localhost:8000/api/translate \
  -F "file=@/path/to/document.pdf" \
  -F "target_language=en"
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Check job status:
```bash
curl http://localhost:8000/api/status/550e8400-e29b-41d4-a716-446655440000
```

Expected response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": ""
}
```

### Check job result (placeholder):
```bash
curl http://localhost:8000/api/result/550e8400-e29b-41d4-a716-446655440000
```

Expected response (while job is queued):
```json
{
  "detail": "Job is not completed yet. Current status: queued"
}
```

## File Storage Location

Uploaded files are stored in:
```
./data/jobs/{job_id}/input.pdf
./data/jobs/{job_id}/job.json
```

Example:
```
./data/jobs/550e8400-e29b-41d4-a716-446655440000/input.pdf
./data/jobs/550e8400-e29b-41d4-a716-446655440000/job.json
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Variables:
- `OPENAI_API_KEY` - Your OpenAI API key (for future use)
- `STORAGE_DIR` - Directory for file storage
- `REDIS_URL` - Redis connection URL
- `API_BASE_URL` - Backend API base URL for frontend