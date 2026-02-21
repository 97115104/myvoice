#!/bin/bash

# My Voice Setup Script
# Installs dependencies and sets up the environment

set -e

echo "╔═══════════════════════════════════════╗"
echo "║          My Voice Setup                ║"
echo "║   Voice Cloning & Text-to-Speech      ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python 3.9+ is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install PyTorch (with CUDA support if available)
echo ""
echo "Installing PyTorch..."

# Detect if CUDA is available
if command -v nvidia-smi &> /dev/null; then
    echo "CUDA detected, installing PyTorch with CUDA support..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
else
    echo "No CUDA detected, installing CPU-only PyTorch..."
    pip install torch torchaudio
fi

# Install other dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Download XTTS model (this will happen on first run, but we can pre-download)
echo ""
echo "Pre-downloading XTTS v2 model..."
echo "(This may take a few minutes, the model is ~2GB)"
python3 -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║          Setup Complete!              ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  python server.py"
echo ""
echo "Then open http://localhost:5000 in your browser"
echo ""
