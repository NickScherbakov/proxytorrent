.PHONY: help install test run docker-build docker-run clean

help:
	@echo "ProxyTorrent - Makefile Commands"
	@echo "================================="
	@echo "install       - Install dependencies"
	@echo "test          - Run unit tests"
	@echo "run           - Run the server locally"
	@echo "docker-build  - Build Docker image"
	@echo "docker-run    - Run with Docker Compose"
	@echo "docker-stop   - Stop Docker containers"
	@echo "clean         - Clean temporary files"

install:
	pip install -r requirements.txt

test:
	python3 test_unit.py

run:
	python3 server.py

docker-build:
	docker build -t proxytorrent:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf /tmp/proxytorrent 2>/dev/null || true
