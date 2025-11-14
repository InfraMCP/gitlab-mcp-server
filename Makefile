.PHONY: help install install-dev test test-cov lint format clean build publish

help:
	@echo "GitLab MCP Server - Development Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  install       Install package in production mode"
	@echo "  install-dev   Install package with development dependencies"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  lint          Run pylint code quality checks"
	@echo "  format        Format code with black"
	@echo "  clean         Remove build artifacts and cache files"
	@echo "  build         Build distribution packages"
	@echo "  publish       Publish to PyPI (requires credentials)"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=gitlab_mcp_server --cov-report=term --cov-report=html

lint:
	pylint src/gitlab_mcp_server

format:
	black src/gitlab_mcp_server tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*
