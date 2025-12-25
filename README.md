# Obsidian MCP Chat

This project implements a proof-of-concept chat application that uses a Large Language Model (LLM) to interact with an Obsidian knowledge vault via a **Model Context Protocol (MCP)** server. This approach strictly separates the LLM's reasoning from the knowledge base access, fulfilling the user's requirement to use a tool-calling mechanism instead of traditional RAG (Retrieval-Augmented Generation).

The system is designed to enforce a strict set of rules (System and Developer Prompts) that mandate the LLM to use the Obsidian vault as the **primary and authoritative source of truth**.

## 🚀 Architecture

The application is composed of three main components, all implemented in Python:

1.  **Obsidian Mock Vault (`vault/`)**: A directory containing sample Markdown files to simulate the user's notes.
2.  **MCP Server (`mcp_server.py`)**: A FastAPI application that exposes a REST API to query the mock vault. This acts as the "access gate" for the LLM.
3.  **Chat Client (`chat_client.py`)**: A command-line application that uses the OpenAI API's tool-calling feature. It injects the user's strict prompts and uses the MCP Server functions as its available tools.

## 🛠️ Setup and Installation

### Prerequisites

*   Python 3.11+
*   An OpenAI API Key

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/watermellon2018/chat_obsidian.git
    cd chat_obsidian
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the root directory and add your OpenAI API key. The MCP server URL is configured to run locally on port 8000 by default.

    **.env**
    ```
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    MCP_SERVER_URL="http://localhost:8000"
    ```

## 💻 Usage

The system requires two separate processes to run: the MCP Server and the Chat Client.

### 1. Start the MCP Server

The server must be running to handle the LLM's tool calls.

```bash
# Ensure you are in the virtual environment
source venv/bin/activate
uvicorn mcp_server:app --host 0.0.0.0 --port 8000
```
*Note: Keep this terminal window open and running.*

### 2. Start the Chat Client

Open a second terminal window, activate the virtual environment, and run the client.

```bash
# Ensure you are in the virtual environment
source venv/bin/activate
python chat_client.py
```

The client will start, and you can begin asking questions. The LLM will automatically use the MCP tools to search your mock Obsidian vault before generating a response, strictly following the rules defined in `prompts.py`.

**Example Interaction:**

```
--- Obsidian MCP Chat Client ---
...
User: What are the key Python best practices I noted?
-> Calling MCP Tool: search_vault with args: {"query": "Python Best Practices"}
<- Tool Result (partial): [{"path": "Concepts/Python_Best_Practices.md", "snippet": "--- tags: [Python, BestPractices, CleanCode] --- # Python Best Practices The project should adhere to **PEP 8** for code style. Key principles include: 1. Readability: Code is read more often than it is written. Use clear variable names. 2. Virtual Environments: Always use `venv` or similar to isolate dependencies. 3. Type Hinting: Use type hints for better maintainability and static analysis. 4. Async/Await: For I/O-bound tasks like network requests (e.g., calling the MCP server), use `async` and `await` with libraries like `httpx` and `fastapi` to maximize performance. Source: My notes from the "Clean Code in Python" book."}
Assistant: 
**From your Obsidian notes:**

Your note in `Concepts/Python_Best_Practices.md` outlines several key Python best practices:

1.  **Readability**: Code should be easy to read, and you should use clear variable names.
2.  **Virtual Environments**: Always use `venv` or similar tools to isolate dependencies.
3.  **Type Hinting**: Use type hints for better maintainability and static analysis.
4.  **Async/Await**: For I/O-bound tasks like network requests (such as calling the MCP server), you noted that using `async` and `await` with libraries like `httpx` and `fastapi` helps maximize performance.

The note also mentions that the project should adhere to **PEP 8** for code style.

**Additional explanation (not from your notes):**

These practices align with modern Python development standards, emphasizing maintainability, performance, and clarity. The use of `async/await` is particularly relevant for applications like this chat client, which relies on network communication with the MCP server.
```

## 📄 Files

| File | Description |
| :--- | :--- |
| `chat_client.py` | The main chat application, handling LLM interaction and tool-calling logic. |
| `mcp_server.py` | The FastAPI server implementing the mock MCP API endpoints. |
| `vault_manager.py` | Utility functions for reading and searching the mock Obsidian vault. |
| `prompts.py` | Contains the strict `SYSTEM_PROMPT`, `DEVELOPER_PROMPT`, and `TOOL_POLICY` for the LLM. |
| `vault/` | Directory containing mock Obsidian notes (`.md` files). |
| `requirements.txt` | List of Python dependencies. |
| `ARCHITECTURE.md` | Detailed design document for the system. |
| `.env` | Environment variables for configuration (e.g., API key). |
