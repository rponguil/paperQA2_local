# Installation Guide

This guide provides detailed instructions for setting up the `paperqa2-local` project and its dependencies on your local machine.

## 1. System Dependencies

Before installing the Python packages, you need to ensure you have the required external services running.

### Python

This project requires **Python 3.11 or newer**. You can check your Python version by running:
```sh
python3 --version
```
If you need to manage multiple Python versions, we recommend using a tool like [pyenv](https://github.com/pyenv/pyenv).

### GROBID Server

GROBID is used for high-quality extraction of text and metadata from scientific PDFs. The application expects a running GROBID server instance. The easiest way to run GROBID is by using Docker.

1.  **Install Docker**: If you don't have Docker, follow the official installation instructions for your operating system: [Get Docker](https://docs.docker.com/get-docker/).

2.  **Run the GROBID container**: Open your terminal and run the following command to pull the GROBID image and start the server.
    ```sh
    docker run -t --rm --init -p 8070:8070 lfoppiano/grobid:0.8.0
    ```
    This command will:
    - `-p 8070:8070`: Map port 8070 on your local machine to port 8070 in the container.
    - `--rm`: Automatically remove the container when it exits.
    - `--init`: Ensures proper handling of processes within the container.

3.  **Verify GROBID is running**: Open your web browser and navigate to `http://localhost:8070`. You should see the GROBID service documentation. You can also check if the service is alive by visiting `http://localhost:8070/api/isalive`, which should return `true`.

### Local LLM Server (Ollama)

The system is designed to connect to a local Large Language Model provider. The primary supported service is [Ollama](https://ollama.ai/).

1.  **Install Ollama**: Follow the instructions on the [Ollama website](https://ollama.ai/download) to download and install it for your operating system.

2.  **Pull a model**: Once Ollama is running, you need to pull the models you intend to use. The project is configured to use `llama3.2:8b` for generation and `mxbai-embed-large` for embeddings by default. You can pull them with the following commands:
    ```sh
    ollama pull llama3.2:8b
    ollama pull mxbai-embed-large
    ```
    You can verify the installed models by running `ollama list`.

## 2. Project Setup

With the system dependencies in place, you can now set up the Python environment for the project.

### Step-by-Step Installation

1.  **Clone the Repository**:
    Get the project source code by cloning its Git repository.
    ```sh
    git clone <repository-url>
    cd paperqa2-local
    ```

2.  **Run the Automated Setup Script**:
    The project includes a setup script that automates the creation of a virtual environment and the installation of all required Python packages.
    ```sh
    ./scripts/setup.sh
    ```
    This script performs the following actions:
    -   Verifies your Python version.
    -   Creates a local virtual environment in a directory named `venv`.
    -   Installs all packages listed in `requirements/base.txt` and `requirements/dev.txt`.
    -   Installs the `paperqa2-local` package in "editable" mode (`-e .`), so any changes you make to the source code are immediately available.

3.  **Activate the Virtual Environment**:
    After the setup script is finished, you must "activate" the virtual environment in your terminal to use the project and its dependencies.
    ```sh
    source venv/bin/activate
    ```
    Your terminal prompt should now be prefixed with `(venv)`, indicating that the virtual environment is active.

## 3. Verifying the Installation

To ensure everything is working correctly, you can run the project's unit tests.

```sh
# Make sure your virtual environment is active
source venv/bin/activate

# Run the test suite
pytest
```
If all tests pass, your development environment is set up correctly. You can now run the example code from the `README.md` or start developing new features.
