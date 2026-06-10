# New Parley

New Parley is an authoring platform and interactive playground designed to construct structured, human-like historical dialogues using Large Language Models (LLMs) and Hybrid Retrieval-Augmented Generation (RAG).

## Getting Started

### Prerequisites

This project utilizes a dual Python (FastAPI) and Node.js (Vue 3 / Vite) stack. Ensure you have the following prerequisites installed:

- **Git:** For version control.
- **Python 3.10+:** The runtime environment for the FastAPI backend.
- **Node.js (v18+):** The runtime environment for building and running the Vite frontend interface.
- **uv:** A fast Python package installer. Run `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` to install.
- **NVIDIA CUDA Toolkit (Optional):** Highly recommended if running Whisper or local embedding models with GPU acceleration.

### Installation & Run

We provide a custom script, `go.bat`, to handle environment setup, dependency management, and running the application in a unified environment.

#### Running Both Backend and Frontend

To set up your virtual environment, install Python/Node dependencies, and start the development servers simultaneously, execute:

```bash
go.bat
```

- The FastAPI backend will run on `http://127.0.0.1:5000`
- The Vite development server will run on `http://localhost:5173`

#### Running Components Individually

If you prefer to run or build components in isolation, you can use the following flags:

```bash
# Start backend service only
go.bat backend

# Start frontend development server only
go.bat frontend

# Compile the frontend assets into the 'dist' folder
go.bat b

# Open a command prompt with the python virtual environment activated
go.bat cmd
```

## Project Structure

- **`backend/`**: Contains the FastAPI server, endpoints, database RAG services, and session orchestrators.
- **`frontend/`**: Contains the Vue 3 application, stores (Pinia), and visual editor canvases (Vue Flow / Rete).