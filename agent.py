#!/usr/bin/env python3
"""
AI Price Comparison Agent

Searches Amazon, eBay, Temu, Walmart, and other e-commerce sites
to find the cheapest price for any product.

Usage:
    python agent.py
    python agent.py "iPhone 15 case"

Requirements:
    pip install -r requirements.txt

Environment:
    ANTHROPIC_API_KEY - Your Anthropic API key
"""

import os
import sys
import json
import re
import anthropic
import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS  # new package name (ddgs >= 0.1)
except ImportError:
    from duckduckgo_search import DDGS  # legacy fallback

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the web for product prices on shopping sites such as "
            "Amazon, eBay, Temu, Walmart, Best Buy, AliExpress, and others. "
            "Returns titles, URLs, and price snippets from search results. "
            "Use targeted queries like 'iphone 15 case price site:amazon.com' "
            "or 'iphone 15 case cheapest price' to get relevant results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query. Include site names or 'price' / 'buy' "
                        "keywords to get pricing results."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of results to return (1-10, default 6).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": (
            "Fetch the HTML of a product or search page and return the "
            "visible text so prices and product details can be extracted. "
            "Use this when a search result URL looks like a direct product "
            "listing that may contain a specific price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the product page to fetch.",
                },
            },
            "required": ["url"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def search_web(query: str, max_results: int = 6) -> str:
    """Search the web using DuckDuckGo (no API key required)."""
    max_results = max(1, min(max_results, 10))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No search results found."
        parts = []
        for r in results:
            parts.append(
                f"Title: {r.get('title', '')}\n"
                f"URL: {r.get('href', '')}\n"
                f"Snippet: {r.get('body', '')}"
            )
        return "\n---\n".join(parts)
    except Exception as exc:
        return f"Search error: {exc}"


def fetch_page(url: str) -> str:
    """Fetch a webpage and return its cleaned text content (max 4000 chars)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return f"Error: request timed out for {url}"
    except requests.exceptions.RequestException as exc:
        return f"Error fetching {url}: {exc}"

    try:
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove non-content tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg"]):
            tag.decompose()

        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else "(no title)"

        body_text = soup.get_text(separator=" ", strip=True)
        # Collapse excessive whitespace
        body_text = re.sub(r"\s{2,}", " ", body_text)

        # Trim to avoid blowing token budget
        if len(body_text) > 4000:
            body_text = body_text[:4000] + " ..."

        return f"Title: {title_text}\nURL: {url}\n\n{body_text}"
    except Exception as exc:
        return f"Error parsing {url}: {exc}"


def execute_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return its string result."""
    if name == "search_web":
        return search_web(
            query=tool_input["query"],
            max_results=tool_input.get("max_results", 6),
        )
    if name == "fetch_page":
        return fetch_page(url=tool_input["url"])
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert price-comparison shopping agent.

Your goal is to find the cheapest current price for the user's product across
multiple e-commerce platforms including (but not limited to):
  - Amazon
  - eBay
  - Temu
  - Walmart
  - Best Buy
  - AliExpress
  - Target

Strategy:
1. Run several targeted web searches — one broad search and then
   site-specific searches (e.g., include "site:amazon.com" or mention
   "amazon price", "ebay listing", "temu", etc.).
2. If a search result looks like a real product page with a price in the
   URL or title, use fetch_page to get the exact price.
3. Collect at least 3–5 price data points before drawing conclusions.
4. At the end, present a clear, ranked comparison table:

   | Store      | Product Name            | Price   | URL          |
   |------------|-------------------------|---------|--------------|
   | Amazon     | ...                     | $XX.XX  | https://...  |
   | eBay       | ...                     | $XX.XX  | https://...  |
   | ...        | ...                     | ...     | ...          |

   Then state the cheapest option clearly.

Important:
- Use real prices only — do not invent or estimate prices.
- If you cannot find a price for a store, note "price not found".
- Skip sponsored/ad results when possible; prefer organic listings.
- Be concise in intermediate reasoning; be thorough in the final summary.
"""


def run_agent(product_query: str) -> None:
    """Run the price comparison agent for a given product query."""
    print(f"\nSearching for: {product_query}")
    print("=" * 60)

    messages = [
        {
            "role": "user",
            "content": (
                f"Find the cheapest price for: {product_query}\n\n"
                "Search Amazon, eBay, Temu, Walmart, Best Buy, and any other "
                "relevant stores. Present a price comparison table sorted from "
                "cheapest to most expensive, and highlight the best deal."
            ),
        }
    ]

    max_turns = 20  # Safety cap on tool-use iterations

    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Print any text Claude produces this turn
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(block.text)

        # Done — no more tool calls
        if response.stop_reason == "end_turn":
            break

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            # Append assistant turn (with tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute all requested tools
            tool_results = []
            for tu in tool_uses:
                label = tu.input.get("query") or tu.input.get("url") or tu.name
                print(f"  [tool: {tu.name}] {label[:80]}")
                result = execute_tool(tu.name, tu.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason
            break

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  AI Price Comparison Agent")
    print("  Powered by Claude claude-opus-4-6")
    print("=" * 60)

    # Allow passing a product as a command-line argument
    if len(sys.argv) > 1:
        product = " ".join(sys.argv[1:])
        run_agent(product)
        return

    # Interactive mode
    while True:
        print("\nEnter a product to find the cheapest price (or 'quit' to exit):")
        try:
            product = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not product:
            continue

        if product.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        run_agent(product)


if __name__ == "__main__":
    main()
