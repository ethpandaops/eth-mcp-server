.PHONY: help install install-dev dev test coverage lint format clean docker pre-commit

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make dev          - Run in development mode"
	@echo "  make test         - Run all tests"
	@echo "  make coverage     - Generate coverage report"
	@echo "  make lint         - Run linters (flake8, mypy, bandit)"
	@echo "  make format       - Format code (black, isort)"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make docker       - Build Docker image"
	@echo "  make pre-commit   - Install and run pre-commit hooks"

# Install production dependencies
install:
	pip install --upgrade pip setuptools wheel
	pip install -e .

# Install development dependencies
install-dev:
	pip install --upgrade pip setuptools wheel
	pip install -e ".[dev]"
	pre-commit install

# Run in development mode
dev:
	python -m src.server

# Run all tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
coverage:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "Coverage report generated in htmlcov/index.html"

# Run linters
lint: lint-flake8 lint-mypy lint-bandit

lint-flake8:
	@echo "Running flake8..."
	flake8 src/ tests/

lint-mypy:
	@echo "Running mypy..."
	mypy src/

lint-bandit:
	@echo "Running bandit security linter..."
	bandit -r src/ -ll

# Format code
format: format-black format-isort

format-black:
	@echo "Running black formatter..."
	black src/ tests/

format-isort:
	@echo "Running isort import sorter..."
	isort src/ tests/

# Check formatting without modifying files
check-format:
	@echo "Checking black formatting..."
	black --check src/ tests/
	@echo "Checking isort formatting..."
	isort --check-only src/ tests/

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type f -name ".DS_Store" -delete

# Build Docker image
docker:
	docker build -t eth-mcp-server:latest .

# Run pre-commit hooks
pre-commit:
	pre-commit run --all-files

# Install pre-commit hooks
pre-commit-install:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Update pre-commit hooks
pre-commit-update:
	pre-commit autoupdate

# Run security check
security:
	safety check
	bandit -r src/ -ll -f json -o bandit-report.json

# Generate requirements files
requirements:
	pip-compile pyproject.toml -o requirements.txt
	pip-compile --extra dev pyproject.toml -o requirements-dev.txt

# Run the server with environment variables
run:
	python -m src.server

# Quick test run (no coverage)
test-quick:
	pytest tests/ -v --tb=short -x

# Run only unit tests
test-unit:
	pytest tests/ -v --tb=short -m "unit"

# Run only integration tests
test-integration:
	pytest tests/ -v --tb=short -m "integration"

# Type check with mypy
type-check:
	mypy src/ --show-error-codes --pretty

# Build distribution packages
build:
	python -m build

# Upload to PyPI (use with caution)
upload:
	python -m twine upload dist/*

# Upload to TestPyPI
upload-test:
	python -m twine upload --repository testpypi dist/*