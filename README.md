# Proxmox-VE-Admin-Docs-MCP

This repository contains the full [Proxmox VE Administration Guide](https://pve.proxmox.com/pve-docs/pve-admin-guide.html) converted to a single Markdown file (`Proxmox-VE-Admin-Docs-MCP.md`), exposed as a functional **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)** server so that any MCP-compatible AI assistant can search and retrieve documentation.

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_sections` | Returns all chapter headings in the guide |
| `get_section(heading)` | Returns the full Markdown content of a named chapter |
| `search_docs(query, max_results)` | Keyword search; returns ranked snippets with their section headings |

## Quick start

### Prerequisites

- Python 3.10 or later

### Install

```bash
pip install -r requirements.txt
```

### Run (stdio transport — for Claude Desktop, etc.)

```bash
python server.py
```

### Run (SSE / HTTP transport)

```bash
python server.py --transport sse
```

The SSE server listens on `http://127.0.0.1:8000` by default.

## Claude Desktop configuration

Add the following block to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "proxmox-docs": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Source

- Original HTML guide: <https://pve.proxmox.com/pve-docs/pve-admin-guide.html>
- Markdown conversion: `Proxmox-VE-Admin-Docs-MCP.md`
