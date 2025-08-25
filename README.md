# PaperQA2 Local

**PaperQA2 Local** is a Retrieval-Augmented Generation (RAG) system designed for local execution, based on the principles of PaperQA2. It leverages the power of [GROBID](https://github.com/kermitt2/grobid) for high-quality PDF extraction and can connect to local Large Language Models (LLMs) through services like Ollama or LM Studio.

This project aims to provide a powerful, private, and extensible framework for asking questions to scientific documents.

## 🌟 Key Features (Phase 1 Implemented)

*   **High-Quality PDF Extraction**: Uses GROBID to parse scientific papers, extracting structured metadata, sections, and references with high accuracy.
*   **Local LLM Integration**: Connects to local LLM services (currently supporting Ollama) for text generation and embeddings, ensuring your data remains private.
*   **Hybrid Extraction Strategy**: Intelligently chooses between the high-accuracy GROBID extractor and a faster `PyPDF`-based fallback.
*   **Asynchronous Architecture**: Built with `asyncio` for efficient, non-blocking operations.
*   **Test-Driven**: Core components are verified with a suite of unit tests.

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.11+
*   A running [GROBID](https://grobid.readthedocs.io/en/latest/Running-Grobid/) server (typically at `http://localhost:8070`). You can easily start one using Docker:
    ```sh
    docker run -t --rm --init -p 8070:8070 lfoppiano/grobid:0.8.0
    ```
*   A running local LLM service like [Ollama](https://ollama.ai/) (typically at `http://localhost:11434`).

### ⚙️ Installation

You can set up the development environment using the provided script. This will create a virtual environment, install all necessary dependencies, and make the project's code available.

1.  **Clone the repository:**
    ```sh
    git clone <repository-url>
    cd paperqa2-local
    ```

2.  **Run the setup script:**
    This script will check your Python version, create a virtual environment in `./venv`, and install all required packages.
    ```sh
    ./scripts/setup.sh
    ```

3.  **Activate the virtual environment:**
    To use the project, you need to activate this environment in your shell session:
    ```sh
    source venv/bin/activate
    ```

### 📝 Basic Usage Example

Here is a simple example of how to use the core components programmatically. Create a Python file (e.g., `example.py`), place a PDF in the same directory (e.g., `my_paper.pdf`), and add the following code:

```python
import asyncio
import os
from paperqa2_local.extractors import GrobidExtractor, FallbackExtractor, HybridExtractor
from paperqa2_local.llm import LocalLLMManager, LocalLLMConfig

# Make sure you have a PDF file to test with.
# For this example, we'll create a dummy file if it doesn't exist.
PDF_PATH = "my_paper.pdf"
if not os.path.exists(PDF_PATH):
    print(f"'{PDF_PATH}' not found. Please place a sample PDF with this name in the directory.")
    # In a real scenario, you would have your own PDFs.
    # For this example to run, you must provide a PDF file.
    exit()

async def main():
    # --- 1. Setup Extractors ---
    # This assumes you have a GROBID server running at the default URL.
    print("Initializing extractors...")
    grobid_extractor = GrobidExtractor()
    fallback_extractor = FallbackExtractor()

    # The HybridExtractor will try GROBID first, then fallback.
    hybrid_extractor = HybridExtractor(
        grobid_extractor=grobid_extractor,
        fallback_extractor=fallback_extractor
    )

    # --- 2. Extract a PDF ---
    print(f"Extracting content from '{PDF_PATH}'...")
    try:
        extracted_doc = await hybrid_extractor.extract_pdf(PDF_PATH)
        print(f"-> Extraction successful using: {extracted_doc.extraction_method}")
        print(f"-> Title: {extracted_doc.metadata.title}")
        if extracted_doc.metadata.abstract:
            print(f"-> Abstract (first 100 chars): {extracted_doc.metadata.abstract[:100]}...")
        print("-" * 20)
    except Exception as e:
        print(f"An error occurred during extraction: {e}")
        return

    # --- 3. Setup LLM Manager ---
    # This assumes you have an Ollama server running.
    print("Initializing LLM Manager...")
    llm_config = LocalLLMConfig()
    llm_manager = LocalLLMManager(llm_config)

    # --- 4. Generate a response ---
    print("Asking the LLM a question about the document...")
    try:
        # Create a simple prompt using the extracted abstract
        context = extracted_doc.metadata.abstract or extracted_doc.text[:1000]
        question = "What is the main conclusion of this text?"

        # In a real RAG system, this would be more sophisticated.
        full_prompt = f"Based on the following text, answer the question.\n\nText: '{context}'\n\nQuestion: {question}"

        response = await llm_manager.generate_response(full_prompt)
        print(f"-> LLM Response: {response}")
    except Exception as e:
        print(f"An error occurred while communicating with the LLM: {e}")
    finally:
        # Clean up the aiohttp session
        await llm_manager.close()


if __name__ == "__main__":
    asyncio.run(main())

```

## 🧪 Running Tests

To run the full suite of unit tests, make sure you have the development dependencies installed (the `setup.sh` script handles this) and then run:

```sh
# Activate the virtual environment first
source venv/bin/activate

# Run pytest
pytest
```
