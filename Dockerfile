# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p static/swagger templates

# Set environment variables
ENV FLASK_CONFIG=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "run.py"]

# docker-compose.yml
version: '3.8'

services:
  doctype-inspector:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_CONFIG=production
      - SECRET_KEY=${SECRET_KEY:-change-this-secret-key}
      - HOST=0.0.0.0
      - PORT=5000
    volumes:
      - ./static:/app/static
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3

# .dockerignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env
.venv
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# deploy.sh (Deployment script)
#!/bin/bash

# ERPNext DocType Inspector Deployment Script
# This script sets up and runs the application

set -e

echo "🚀 ERPNext DocType Inspector Deployment"
echo "======================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing requirements..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/swagger
mkdir -p templates

# Set environment variables
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
    echo "🔑 Generated SECRET_KEY: $SECRET_KEY"
    echo "⚠️  Save this SECRET_KEY for production use!"
fi

if [ -z "$FLASK_CONFIG" ]; then
    export FLASK_CONFIG="development"
fi

# Run the application
echo "🌟 Starting ERPNext DocType Inspector..."
echo "Configuration: $FLASK_CONFIG"
echo "Access the application at: http://localhost:5000"
echo ""
echo "To stop the application, press Ctrl+C"
echo ""

python run.py

# Makefile
.PHONY: install run clean test docker-build docker-run help

# Default target
help:
	@echo "ERPNext DocType Inspector - Available Commands:"
	@echo ""
	@echo "  install     - Install dependencies and setup virtual environment"
	@echo "  run         - Run the application in development mode"
	@echo "  run-prod    - Run the application in production mode"
	@echo "  clean       - Clean up generated files and cache"
	@echo "  test        - Run tests (when implemented)"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run application using Docker"
	@echo "  help        - Show this help message"

install:
	@echo "📦 Setting up ERPNext DocType Inspector..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	mkdir -p static/swagger
	mkdir -p templates
	@echo "✅ Setup complete! Run 'make run' to start the application."

run:
	@echo "🚀 Starting development server..."
	@export FLASK_CONFIG=development && ./venv/bin/python run.py

run-prod:
	@echo "🚀 Starting production server..."
	@export FLASK_CONFIG=production && ./venv/bin/python run.py

clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf static/swagger/*.json
	@echo "✅ Cleanup complete!"

test:
	@echo "🧪 Running tests..."
	@echo "Tests not implemented yet. Coming soon!"

docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t erpnext-doctype-inspector .
	@echo "✅ Docker image built successfully!"

docker-run:
	@echo "🐳 Starting application with Docker..."
	docker-compose up --build
	@echo "✅ Application started! Access at http://localhost:5000"

# Installation script for different platforms
# install.sh
#!/bin/bash

# ERPNext DocType Inspector Installation Script
# Supports Linux, macOS, and Windows (via WSL/Git Bash)

set -e

echo "🚀 ERPNext DocType Inspector Installation"
echo "========================================="

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    CYGWIN*)    MACHINE=Cygwin;;
    MINGW*)     MACHINE=MinGw;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "🖥️  Operating System: $MACHINE"

# Check dependencies
echo "🔍 Checking dependencies..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
    echo "✅ Python 3 found: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    echo "   Visit: https://www.python.org/downloads/"
    exit 1
fi

# Check pip
if python3 -m pip --version &> /dev/null; then
    echo "✅ pip found"
else
    echo "❌ pip not found. Installing pip..."
    python3 -m ensurepip --upgrade
fi

# Check git (optional)
if command -v git &> /dev/null; then
    echo "✅ Git found"
else
    echo "⚠️  Git not found (optional)"
fi

# Create project directory if it doesn't exist
if [ ! -f "app.py" ]; then
    echo "📁 Setting up project structure..."
    mkdir -p templates static/swagger
    echo "✅ Project structure created"
fi

# Create virtual environment
echo "📦 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment (different for different shells)
if [ -f "venv/bin/activate" ]; then
    # Linux/Mac
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    # Windows
    source venv/Scripts/activate
else
    echo "❌ Could not find virtual environment activation script"
    exit 1
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python packages..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "Creating requirements.txt..."
    cat > requirements.txt << EOF
Flask==3.0.0
Flask-WTF==1.2.1
WTForms==3.1.1
requests==2.31.0
Werkzeug==3.0.1
EOF
    pip install -r requirements.txt
fi

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure you have created all the application files (app.py, templates, etc.)"
echo "2. Set up your ERPNext API credentials"
echo "3. Run the application:"
echo "   - Development: ./deploy.sh"
echo "   - Or manually: source venv/bin/activate && python run.py"
echo ""
echo "🌐 The application will be available at: http://localhost:5000"