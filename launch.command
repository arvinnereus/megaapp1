#!/bin/bash
# Double-click this file to launch the All-in-One Business App locally.
# It will open your browser automatically.

cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  Launching All-in-One Business App..."
echo "============================================"
echo ""

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "  First run -- setting up..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt -q
    [ ! -f .env ] && cp .env.example .env
else
    source .venv/bin/activate
fi

echo "  Starting server on http://localhost:8000"
echo "  Press Ctrl+C to stop."
echo ""

# Open browser after a short delay
(sleep 2 && open http://localhost:8000/admin/dashboard) &

# Run the app
python app.py
