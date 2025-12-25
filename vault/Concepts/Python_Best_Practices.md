---
tags: [Python, BestPractices, CleanCode]
---
# Python Best Practices

The project should adhere to **PEP 8** for code style. Key principles include:

1.  **Readability**: Code is read more often than it is written. Use clear variable names.
2.  **Virtual Environments**: Always use `venv` or similar to isolate dependencies.
3.  **Type Hinting**: Use type hints for better maintainability and static analysis.
4.  **Async/Await**: For I/O-bound tasks like network requests (e.g., calling the MCP server), use `async` and `await` with libraries like `httpx` and `fastapi` to maximize performance.

**Source:** My notes from the "Clean Code in Python" book.
