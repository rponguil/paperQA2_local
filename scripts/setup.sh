#!/bin/bash
# Script to set up the development environment for PaperQA2 Local

set -e

echo "🚀 Setting up PaperQA2 Local development environment..."

# 1. Check for Python 3.11+
echo "🐍 Checking Python version..."
# Using python3 to be explicit
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ is required."'
if [ $? -ne 0 ]; then
    echo "❌ Error: Python 3.11+ is required. Please install it and try again."
    exit 1
fi
echo "✅ Python version check passed."

# 2. Create a virtual environment
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in './$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
else
    echo "📦 Virtual environment already exists."
fi

# 3. Activate the virtual environment and install dependencies
echo "📥 Activating venv and installing dependencies from requirements/base.txt..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements/base.txt
echo "✅ Dependencies installed."

# 4. Install the package in editable mode
echo "🛠️ Installing 'paperqa2-local' in editable mode..."
pip install -e .
echo "✅ Package installed."

# --- The following steps are for future implementation ---

# echo "⚙️ Configuring GROBID..."
# if [ -f "scripts/install_grobid.sh" ]; then
#     ./scripts/install_grobid.sh
# else
#     echo "⚠️ 'scripts/install_grobid.sh' not found. Skipping GROBID setup."
# fi

# echo "🤖 Detecting local LLMs..."
# if command -v paperqa2-local &> /dev/null; then
#     # This part will be implemented later
#     echo "✅ Setup for local LLM detection will be implemented."
# else
#     echo "⚠️ 'paperqa2-local' command not found. Skipping LLM detection."
# fi

# echo "🧪 Running system tests..."
# if [ -f "scripts/test_system.sh" ]; then
#     ./scripts/test_system.sh
# else
#     echo "⚠️ 'scripts/test_system.sh' not found. Skipping system tests."
# fi

echo ""
echo "✅ Development setup completed!"
echo "👉 To activate the environment, run: source $VENV_DIR/bin/activate"
echo "👉 To get started, you can try running: paperqa2-local --help (Note: CLI is not yet implemented)"
