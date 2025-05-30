# GPT Newspaper MCP Server

This directory contains the Model Context Protocol (MCP) server and client implementation for the GPT Newspaper project.

## Prerequisites

- Python 3.11 or higher
- UV package manager installed
- Required environment variables set in `.env` file:
  - Tavily API key
  - Anthropic API key

## Running the Server

The MCP server handles newspaper generation requests and serves the content via SSE (Server-Sent Events).

To run the server:

```bash
uv run .\mcp_server\server.py
```

The server will start and listen for incoming connections on the default port.

## Running the Client

The MCP client connects to the server and requests newspaper content for specified topics.

To run the client:

```bash
uv run .\mcp_server\client.py
``` 