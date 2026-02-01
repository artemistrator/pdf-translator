# Setup Guide

## Prerequisites

- Python 3.11
- Node.js 18+
- Docker & Docker Compose
- pnpm (recommended) or npm

## Installation

1. **Install dependencies:**
```bash
make install
```

2. **Start Redis:**
```bash
make redis-up
```

3. **Start development servers:**
```bash
# Terminal 1 - API
make api-dev

# Terminal 2 - Web
make web-dev
```

Or start both with:
```bash
make dev
```

## Environment Variables

Create `.env` files:

**Root `.env`:**
```bash
cp .env.example .env
```

**Web `.env`:**
```bash
cp apps/web/.env.example apps/web/.env
```

## Ports

- API: http://localhost:8000
- Web: http://localhost:3000
- Redis: localhost:6379

## API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation