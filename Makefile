.PHONY: install redis-up redis-down api-install api-dev api-smoke api-smoke-full api-regression-pdf api-print-paths api-python api-openai-version api-selfcheck api-importcheck api-playwright-install web-install web-dev dev lint format help doctor

help:
	@echo "Document Translator - Development Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make doctor          - Check system requirements"
	@echo "  make install         - Install all dependencies"
	@echo "  make redis-up        - Start Redis container"
	@echo "  make redis-down      - Stop Redis container"
	@echo "  make api-install     - Install API dependencies in venv"
	@echo "  make api-dev         - Start FastAPI development server"
	@echo "  make api-smoke       - Run smoke test"
	@echo "  make api-smoke-full  - Run full smoke test (includes process)"
	@echo "  make api-regression-pdf - Run PDF generation regression test"
	@echo "  make api-playwright-install - Install Playwright Chromium for PDF generation"
	@echo "  make api-print-paths - Print debug paths"
	@echo "  make api-python      - Show Python version in venv"
	@echo "  make api-openai-version - Show OpenAI library version"
	@echo "  make api-selfcheck   - Self-check openai_vision module"
	@echo "  make api-importcheck - Check all module imports"
	@echo "  make web-install     - Install web dependencies"
	@echo "  make web-dev         - Start Next.js development server"
	@echo "  make dev             - Start both API and Web in parallel"
	@echo "  make lint            - Run linters on all code"
	@echo "  make format          - Format all code"

doctor:
	@echo "🔍 Checking system requirements..."
	@echo ""
	
	@echo "Python 3:"
	@if command -v python3 >/dev/null 2>&1; then \
		echo "  ✅ Found: $$(python3 --version)"; \
	else \
		echo "  ❌ Not found"; \
		exit 1; \
	fi
	@echo ""
	
	@echo "Node.js:"
	@if command -v node >/dev/null 2>&1; then \
		echo "  ✅ Found: $$(node --version)"; \
	else \
		echo "  ❌ Not found"; \
		exit 1; \
	fi
	@echo ""
	
	@echo "pnpm:"
	@if command -v pnpm >/dev/null 2>&1; then \
		echo "  ✅ Found: $$(pnpm --version)"; \
	else \
		echo "  ❌ Not found"; \
		echo "     💡 Install pnpm: npm install -g pnpm"; \
		exit 1; \
	fi
	@echo ""
	
	@echo "Docker:"
	@if command -v docker >/dev/null 2>&1; then \
		echo "  ✅ Found: $$(docker --version)"; \
	else \
		echo "  ❌ Not found (needed for Redis)"; \
		exit 1; \
	fi
	@echo ""
	@echo "✅ All requirements satisfied!"

install:
	@echo "Installing dependencies..."
	make api-install
	make web-install
	@echo "Dependencies installed!"

api-install:
	@echo "Installing API dependencies..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@echo "Installing Python packages..."
	@cd apps/api && .venv/bin/pip install -r requirements.txt
	@echo "API dependencies installed!"

web-install:
	@echo "Installing web dependencies..."
	@cd apps/web && pnpm install
	@echo "Web dependencies installed!"

redis-up:
	@echo "Starting Redis..."
	docker-compose -f infra/docker-compose.yml up -d redis
	@echo "Redis is running on localhost:6379"

redis-down:
	@echo "Stopping Redis..."
	docker-compose -f infra/docker-compose.yml down
	@echo "Redis stopped"

api-dev:
	@echo "Starting FastAPI development server..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

api-smoke:
	@echo "Running smoke test..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python smoke_test.py

api-smoke-full:
	@echo "Running full smoke test (including process)..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python smoke_test.py

api-regression-pdf:
	@echo "Running PDF generation regression test..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python regression_pdf_test.py

api-print-paths:
	@echo "Getting debug paths..."
	@curl -s http://localhost:8000/api/debug/paths | jq '.'

web-dev:
	@echo "Starting Next.js development server..."
	@cd apps/web && \
	if ! command -v pnpm >/dev/null 2>&1; then \
		echo "❌ pnpm not found. Please install pnpm: npm install -g pnpm"; \
		exit 1; \
	fi
	@cd apps/web && pnpm dev

dev:
	@echo "Starting development environment..."
	make redis-up
	@echo "Starting API and Web servers..."
	# Run both servers in parallel
	(make api-dev &) && (sleep 3 && make web-dev)

lint:
	@echo "Running linters..."
	@cd apps/api && \
	if [ -d ".venv" ]; then \
		.venv/bin/ruff check . && .venv/bin/black --check .; \
	else \
		echo "⚠️  API venv not found, skipping Python linting"; \
	fi
	@cd apps/web && \
	if command -v pnpm >/dev/null 2>&1; then \
		pnpm lint; \
	else \
		echo "⚠️  pnpm not found, skipping web linting"; \
	fi

format:
	@echo "Formatting code..."
	@cd apps/api && \
	if [ -d ".venv" ]; then \
		.venv/bin/black . && .venv/bin/ruff check . --fix; \
	else \
		echo "⚠️  API venv not found, skipping Python formatting"; \
	fi
	@cd apps/web && \
	if command -v pnpm >/dev/null 2>&1; then \
		pnpm format; \
	else \
		echo "⚠️  pnpm not found, skipping web formatting"; \
	fi

# Venv-safe diagnostic commands
api-python:
	@echo "Python version in venv:"
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python --version

api-openai-version:
	@echo "OpenAI library version:"
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python -c "import openai; print(openai.__version__)"

api-selfcheck:
	@echo "Self-checking openai_vision module:"
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python -c "from openai_vision import analyze_document_images, _create_json_schema; print('✅ openai_vision import OK'); print('✅ _create_json_schema import OK')"

api-importcheck:
	@echo "Checking all module imports:"
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python -c "import main; import openai_vision; import pdf_render; import storage; print('✅ ALL IMPORTS OK')"

api-playwright-install:
	@echo "Installing Playwright Chromium..."
	@cd apps/api && \
	if [ ! -d ".venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make api-install' first."; \
		exit 1; \
	fi
	@cd apps/api && .venv/bin/python -m playwright install chromium
	@echo "✅ Playwright Chromium installed!"