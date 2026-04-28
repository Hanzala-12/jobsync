#!/bin/bash
# Setup script for JobSync

# Create a virtual environment
python3 -m venv venv

# Activate virtual environment
# For Windows Git Bash, use: source venv/Scripts/activate
# For Linux/Mac, use: source venv/bin/activate
echo "Virtual environment created. Activate it with:"
echo "  Windows: source venv/Scripts/activate"
echo "  Linux/Mac: source venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
./venv/Scripts/pip install -r backend/requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    cp backend/.env.example .env
    echo "Created .env file. Please edit it and add your GROQ_API_KEY"
fi

echo "Setup complete! Next steps:"
echo "1. Activate the virtual environment"
echo "2. Edit .env and add your GROQ_API_KEY from https://console.groq.com"
echo "3. Run: bash run.sh"
