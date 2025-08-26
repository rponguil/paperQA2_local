#!/bin/bash

# ==============================================================================
# PaperQA2 Local - End-to-End Test Script
#
# This script provides a simple way to test the full functionality of the
# system. It takes a single PDF file, processes it, and asks a series of
# questions about it.
#
# It's a great way to verify that all components (extraction, indexing,
# and question-answering) are working together correctly.
#
# USAGE:
#   ./scripts/test_system.sh /path/to/your/document.pdf
#
# PARAMETERS:
#   $1: The full path to the PDF file you want to test. This is a required
#       parameter.
#
# ==============================================================================

# --- Configuration ---
set -e # Exit immediately if a command exits with a non-zero status.
GROBID_URL="http://localhost:8070"
OLLAMA_URL="http://localhost:11434"
INDEX_DIR=~/.paperqa2-local/index

# --- Helper Functions ---
function print_header() {
    # Prints a formatted header to the console to make the output readable.
    echo ""
    echo "=============================================================================="
    echo "  $1"
    echo "=============================================================================="
    echo ""
}

function usage() {
    # Prints the usage information and exits.
    echo "Usage: $0 /path/to/your/document.pdf"
    echo ""
    echo "This script runs a full end-to-end test of the paperqa2-local system."
    echo "Please provide the path to a PDF file as the only argument."
    exit 1
}

# --- Script Main Logic ---

# 1. Validate Input Parameter
if [ -z "$1" ]; then
    echo "❌ Error: No PDF file provided."
    usage
fi

PDF_PATH="$1"
if [ ! -f "$PDF_PATH" ]; then
    echo "❌ Error: File not found at '$PDF_PATH'"
    exit 1
fi

# 2. Check Prerequisites
print_header "STEP 1: CHECKING PREREQUISITES"

# Check for venv and activate it
if [ ! -f "venv/bin/activate" ]; then
    echo "❗️ Virtual environment not found. Please run ./scripts/setup.sh first."
    exit 1
fi
source venv/bin/activate
echo "✅ Virtual environment activated."

# Check GROBID server
if ! curl -s --head "$GROBID_URL/api/isalive" | head -n 1 | grep "200 OK" > /dev/null; then
    echo "❌ Error: GROBID server is not responding at $GROBID_URL"
    echo "Please start the GROBID server. Example with Docker:"
    echo "docker run -t --rm --init -p 8070:8070 lfoppiano/grobid:0.8.0"
    exit 1
fi
echo "✅ GROBID server is running."

# Check Ollama server
if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null; then
    echo "❌ Error: Ollama server is not responding at $OLLAMA_URL"
    echo "Please ensure the Ollama application or server is running."
    exit 1
fi
echo "✅ Ollama server is running."


# 3. Clean previous index to ensure a fresh test
print_header "STEP 2: CLEANING PREVIOUS INDEX"
if [ -d "$INDEX_DIR" ]; then
    echo "Removing old index at $INDEX_DIR..."
    rm -rf "$INDEX_DIR"
    echo "✅ Old index removed."
else
    echo "✅ No previous index found. Starting clean."
fi


# 4. Add the document via the CLI
print_header "STEP 3: PROCESSING AND ADDING DOCUMENT"
echo "Running 'paperqa2-local add' on '$PDF_PATH'..."
paperqa2-local add "$PDF_PATH"


# 5. Ask a series of questions via the CLI
print_header "STEP 4: ASKING QUESTIONS ABOUT THE DOCUMENT"
QUESTIONS=(
    "What is the main topic of this document?"
    "Summarize the introduction of this paper in three sentences."
    "What are the main conclusions or findings presented in this document?"
    "Who are the authors of this paper?"
)

for question in "${QUESTIONS[@]}"; do
    echo ""
    echo "---"
    echo "❓ Asking: '$question'"
    echo "---"
    paperqa2-local ask "$question"
done

print_header "✅ TEST COMPLETE"
echo "The script has finished. Review the answers above to check the system's performance."
