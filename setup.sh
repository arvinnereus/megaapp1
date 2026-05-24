#!/bin/bash
# All-in-One Business App — Quick Setup (Mac)
# Run: bash setup.sh

set -e

echo ""
echo "============================================"
echo "  All-in-One Business App — Quick Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is required. Install it from python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
else
    echo "  Virtual environment already exists."
fi

# Activate venv
source .venv/bin/activate
echo "  Activated .venv"

# Install dependencies
echo "  Installing dependencies..."
pip install -r requirements.txt -q

# Create .env if missing
if [ ! -f ".env" ]; then
    echo "  Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "  IMPORTANT: Open .env and add your API keys."
    echo "  At minimum, add OPENAI_API_KEY to enable Jackie AI."
else
    echo "  .env already exists."
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "  Next steps:"
echo "  1. Open .env and add your API keys"
echo "  2. Run the app:  python app.py"
echo "  3. Open:         http://localhost:8000"
echo "  4. Login:        admin / changeme"
echo "  5. Go to Manual & Help for the full guide"
echo ""
echo "  The app auto-seeds demo data on first run."
echo ""
