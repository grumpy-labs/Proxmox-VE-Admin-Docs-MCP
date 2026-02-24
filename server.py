"""
Proxmox VE Administration Guide MCP Server.

Exposes the Proxmox VE Admin Guide (Proxmox-VE-Admin-Docs-MCP.md) as a set
of MCP tools so that any MCP-compatible AI client can search and retrieve
documentation content.

Run via stdio transport (default for Claude Desktop etc.):
    python server.py

Or start the built-in HTTP/SSE server:
    python server.py --transport sse
"""

from __future__ import annotations

import os
import re
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Locate and load the documentation file
# ---------------------------------------------------------------------------

_DOCS_FILE = os.path.join(os.path.dirname(__file__), "Proxmox-VE-Admin-Docs-MCP.md")


def _load_docs() -> str:
    with open(_DOCS_FILE, encoding="utf-8") as fh:
        return fh.read()


_DOCS: str = _load_docs()

# ---------------------------------------------------------------------------
# Section parsing helpers
# ---------------------------------------------------------------------------

# A "section" is any block of content introduced by a level-2 heading (##).
_SECTION_PATTERN = re.compile(r"^(## .+)$", re.MULTILINE)


def _build_section_index(docs: str) -> list[tuple[str, str]]:
    """Return a list of (heading, content) pairs for every ## section."""
    matches = list(_SECTION_PATTERN.finditer(docs))
    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(docs)
        body = docs[start:end].strip()
        sections.append((heading, body))
    return sections


_SECTIONS: list[tuple[str, str]] = _build_section_index(_DOCS)
_SECTION_HEADINGS: list[str] = [h for h, _ in _SECTIONS]

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Proxmox VE Admin Docs",
    instructions=(
        "This server provides access to the full Proxmox VE Administration Guide. "
        "Use 'list_sections' to discover available chapters, 'get_section' to read a "
        "chapter in full, and 'search_docs' to find relevant passages by keyword."
    ),
)


# ---------------------------------------------------------------------------
# Tool: list_sections
# ---------------------------------------------------------------------------


@mcp.tool()
def list_sections() -> list[str]:
    """List all top-level sections (chapters) in the Proxmox VE Administration Guide.

    Returns a list of section headings that can be passed to ``get_section``.
    """
    return _SECTION_HEADINGS


# ---------------------------------------------------------------------------
# Tool: get_section
# ---------------------------------------------------------------------------


@mcp.tool()
def get_section(
    heading: Annotated[
        str,
        "The exact section heading as returned by list_sections, "
        "e.g. '## 7\\. Proxmox VE Storage'",
    ],
) -> str:
    """Retrieve the full markdown content of a named section.

    Args:
        heading: Exact heading string as returned by ``list_sections``.

    Returns:
        The full markdown text of the section, or an error message if not found.
    """
    for h, body in _SECTIONS:
        if h == heading:
            return body
    # Try a case-insensitive partial match as a fallback
    heading_lower = heading.lower()
    for h, body in _SECTIONS:
        if heading_lower in h.lower():
            return body
    return f"Section not found: {heading!r}. Use list_sections() to see available headings."


# ---------------------------------------------------------------------------
# Tool: search_docs
# ---------------------------------------------------------------------------

_MAX_SNIPPET_CHARS = 500  # characters of context returned per hit


@mcp.tool()
def search_docs(
    query: Annotated[str, "One or more keywords or a phrase to search for"],
    max_results: Annotated[int, "Maximum number of matching snippets to return (1–20)"] = 5,
) -> list[dict]:
    """Search the Proxmox VE Administration Guide for relevant content.

    Performs a case-insensitive keyword search across all sections and returns
    the most relevant snippets together with their section heading.

    Args:
        query:       Search term(s) or phrase.
        max_results: How many result snippets to return (default 5, max 20).

    Returns:
        A list of dicts, each with keys ``section`` (heading) and ``snippet``
        (a short excerpt containing the match).  Returns an empty list when
        nothing is found.
    """
    max_results = max(1, min(max_results, 20))
    query_lower = query.lower()
    # Split query into individual tokens for multi-word scoring
    tokens = [t for t in re.split(r"\s+", query_lower) if t]

    results: list[dict] = []

    for heading, body in _SECTIONS:
        body_lower = body.lower()
        # Score = number of token matches in this section
        score = sum(body_lower.count(tok) for tok in tokens)
        if score == 0:
            continue

        # Find the position of the first matching token for a snippet
        first_pos = len(body)
        for tok in tokens:
            pos = body_lower.find(tok)
            if pos != -1 and pos < first_pos:
                first_pos = pos

        # Extract a window of text around the first match
        start = max(0, first_pos - 100)
        end = min(len(body), first_pos + _MAX_SNIPPET_CHARS)
        snippet = body[start:end].strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(body):
            snippet = snippet + "…"

        results.append({"section": heading, "snippet": snippet, "_score": score})

    # Sort by descending score, drop internal score key
    results.sort(key=lambda r: r["_score"], reverse=True)
    for r in results:
        del r["_score"]

    return results[:max_results]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the MCP server.

    Transport defaults to ``stdio``.  Pass ``--transport sse`` (or ``-t sse``)
    to start the built-in HTTP/SSE server instead.
    """
    transport = "stdio"
    args = sys.argv[1:]
    if args:
        if args[0] in ("--transport", "-t"):
            if len(args) < 2:
                print(
                    "Error: --transport requires an argument (stdio or sse)",
                    file=sys.stderr,
                )
                sys.exit(1)
            transport = args[1]
        else:
            print(f"Unknown argument: {args[0]!r}", file=sys.stderr)
            sys.exit(1)

    if transport not in ("stdio", "sse"):
        print(f"Unsupported transport: {transport!r}. Use 'stdio' or 'sse'.", file=sys.stderr)
        sys.exit(1)

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
