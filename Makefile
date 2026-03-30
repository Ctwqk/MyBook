# Makefile for MyBook Project

.PHONY: help install dev test test-coverage docker-up docker-down lint clean

# Help
help:
	@echo "MyBook - 长篇网文生成系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install          - 安装依赖"
	@echo "  make dev              - 开发模式"
	@echo "  make test             - 运行测试"
	@echo "  make test-coverage    - 运行测试并生成覆盖率报告"
	@echo "  make docker-up        - 启动 Docker 容器"
	@echo "  make docker-down      - 停止 Docker 容器"
	@echo "  make lint             - 代码检查"
	@echo "  make clean            - 清理临时文件"

# Install dependencies
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Development
dev:
	docker-compose -f docker-compose.dev.yml up

# Tests
test:
	cd backend && pytest -v

# Test with coverage
test-coverage:
	cd backend && pytest --cov=app --cov-report=html --cov-report=term

# Docker
docker-up:
	docker-compose up -d
	@echo "等待服务启动..."
	@sleep 5
	@echo "服务已启动:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - Backend: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"

docker-down:
	docker-compose down

docker-build:
	docker-compose build

# Lint
lint:
	cd backend && ruff check app/
	cd backend && mypy app/ || true

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	cd backend && rm -rf .coverage htmlcov

# Database
db-init:
	cd backend && python run.py

# Run backend
run-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
run-frontend:
	cd frontend && npm run dev
