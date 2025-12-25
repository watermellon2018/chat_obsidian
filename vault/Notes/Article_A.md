---
tags: [LLM, MCP, Architecture]
---
# Model Context Protocol (MCP)

MCP is a protocol designed to provide a structured, tool-based interface for Large Language Models (LLMs) to access external knowledge bases, such as an Obsidian vault.

**Key Difference from RAG:**
Unlike RAG, which typically involves vector search and embedding, MCP treats the knowledge base as a set of callable tools (like `search_vault` or `read_file_content`). This allows the LLM to make more deliberate, multi-step queries, mimicking a human researcher.

**Source:** This note is based on the article "Beyond RAG: The Rise of Tool-Calling LLMs" which I read last week.
