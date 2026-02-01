# Development Guide

## Project Structure

```
.
├── /apps/
│   ├── /api/          # FastAPI backend
│   │   ├── main.py    # Main FastAPI app
│   │   ├── storage.py # File storage utilities
│   │   └── requirements.txt
│   └── /web/          # Next.js frontend
│       ├── app/       # App router pages
│       ├── public/    # Static assets
│       └── package.json
├── /infra/            # Infrastructure
│   └── docker-compose.yml
├── /docs/             # Documentation
├── /data/             # Storage directory
├── Makefile           # Development commands
└── README.md
```

## Development Commands

```bash
make install     # Install all dependencies
make redis-up    # Start Redis
make redis-down  # Stop Redis
make api-dev     # Start API dev server
make web-dev     # Start Web dev server
make dev         # Start both servers
make lint        # Run code linters
make format      # Format code
```

## Code Quality

### Backend (Python)
- Ruff for linting
- Black for formatting

### Frontend (TypeScript)
- ESLint for linting
- Prettier for formatting

Run quality checks:
```bash
make lint
make format
```

## Storage

Files are stored in `./data` directory. The storage utility in `apps/api/storage.py` provides:

- `save_file()` - Save file content
- `get_file_path()` - Get file path
- `file_exists()` - Check if file exists
- `delete_file()` - Delete file

## Adding New Features

1. **Backend**: Add routes in `apps/api/main.py`
2. **Frontend**: Add pages in `apps/web/app/`
3. **Storage**: Use `storage_manager` from `apps/api/storage.py`
4. **Environment**: Add variables to `.env.example` and root `.env`