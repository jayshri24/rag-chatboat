# Document QA Chatbot

A minimal Document QA Chatbot built with FastAPI, Agno, and NiceGUI that streams agent responses token-by-token and supports PDF upload for document-based question answering.

## Features

- **Streaming Chat**: Real-time token-by-token response streaming via FastAPI
- **PDF Upload & Parsing**: Upload PDF documents and ask questions about their content
- **Session Management**: Persistent chat sessions with document context
- **Async Status Updates**: Non-blocking UI status indicators during processing
- **Modern Architecture**: Built with Python 3.13+, asyncio, and modern typing

## Architecture Overview

### Core Components

1. **FastAPI Backend** (`app/main.py`): REST API with streaming endpoints
2. **Agno Agent** (`app/agent/factory.py`): OpenAI-powered agent orchestration
3. **PDF Parser** (`app/parsing/pdf.py`): PDF text extraction and validation
4. **Session Store** (`app/storage/session_store.py`): Thin layer for PDF knowledge storage
5. **NiceGUI Frontend** (`app/ui.py`): Minimal UI for demonstrating backend functionality


## Setup & Installation

### Prerequisites

- Python 3.13+
- OpenAI API key

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd qa-chatbot
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application**:
   ```bash
   # Option 1: Run FastAPI backend only
   python run.py
   
   # Option 2: Run with NiceGUI UI
   python app/ui.py
   PYTHONPATH=. python3.13 -m app.ui
   ```

6. **Access the application**:
   - FastAPI API: http://16.176.194.5/api
   - NiceGUI UI: http://16.176.194.5/
   - API Swagger Documentation: http://16.176.194.5/docs

## Testing

### Run Tests

```bash
# Run all tests
pytest tests --vv

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/
```

### Test Structure

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test end-to-end flows
- **Test Data** (`tests/data/`): Sample PDF files for testing
```

## API Endpoints

### Streaming Chat
- `POST /chat/stream`: Stream agent responses token-by-token

### PDF Upload
- `POST /upload/pdf`: Upload and parse PDF documents
- Validates file type, size, and content
- Stores parsed text in session knowledge

### Session Management
- `GET /sessions/{session_id}`: Get session information
- `GET /sessions`: List all sessions

## Cursor Configuration

This project was developed using Cursor IDE with the following configuration:

### Linters & Formatters
- **Ruff**: Configured in `pyproject.toml` with strict rules for code quality
- **Black**: Code formatting with 88-character line length
- **MyPy**: Type checking with strict settings for Python 3.13
- **Error Surfacing**: All linter errors surface directly in Cursor's IDE with inline annotations

### Documentation Indexing & IDE Features
- Indexed project documentation in Cursor for instant lookup
- Autocomplete for project modules, classes, and functions
- Quick navigation between tests, source code, and docs

### more check in .cursorsules files
