#!/usr/bin/env python3
"""
Basketball Ranking Bot

Ask anything about basketball rankings — teams, players, stats, positions.
The bot fetches live data and uses Claude to produce a ranked list with analysis.

Usage:
    python bot.py
    python bot.py "rank the top 10 NBA teams right now"
    python bot.py "best point guards this season by assists"
"""

import sys
import re
import anthropic
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the web for current NBA/basketball stats, standings, "
            "rankings, and player data. Use focused queries like "
            "'NBA standings 2025', 'NBA scoring leaders 2024-25 season', "
            "'best NBA teams by record', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for basketball stats or rankings.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-8, default 5).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": (
            "Fetch the content of a stats or sports page to extract detailed "
            "rankings, box scores, or leaderboards. Prefer well-known sources "
            "like ESPN, NBA.com, Basketball-Reference, or CBS Sports."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL of the page to fetch.",
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


def search_web(query: str, max_results: int = 5) -> str:
    max_results = max(1, min(max_results, 8))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
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
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return f"Error: timed out fetching {url}"
    except requests.exceptions.RequestException as exc:
        return f"Error fetching {url}: {exc}"

    try:
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg"]):
            tag.decompose()

        title = soup.find("title")
        title_text = title.get_text(strip=True) if title else "(no title)"

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text)

        if len(text) > 5000:
            text = text[:5000] + " ..."

        return f"Title: {title_text}\nURL: {url}\n\n{text}"
    except Exception as exc:
        return f"Error parsing {url}: {exc}"


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "search_web":
        return search_web(tool_input["query"], tool_input.get("max_results", 5))
    if name == "fetch_page":
        return fetch_page(tool_input["url"])
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert basketball analyst and ranking bot. When a user asks you to
rank teams, players, or anything basketball-related, you:

1. Search for the most current stats and standings for the ongoing or most
   recent NBA season. Always clarify which season the data is from.
2. Fetch stats pages from authoritative sources (ESPN, NBA.com,
   Basketball-Reference, CBS Sports) to get precise numbers.
3. Produce a clean, numbered ranking with the key stat(s) next to each entry.
4. Add a brief (1–2 sentence) analyst note after the ranking explaining the
   most interesting takeaways or surprises.

Formatting rules:
- Use a numbered list for the ranking.
- Show the most relevant stat(s) in parentheses next to each entry,
  e.g. "1. Boston Celtics (68-14, .829 Win%)"
- Keep it concise — one line per ranked item, analysis at the end.
- If data is unavailable for a specific metric, say so honestly.

You can rank anything basketball-related: NBA teams by record, conference
standings, scoring leaders, assists leaders, defensive ratings, rookies,
all-time records, historical seasons, etc.
"""

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


def run_bot(query: str) -> None:
    print(f"\nQuery: {query}")
    print("=" * 60)

    messages = [{"role": "user", "content": query}]
    max_turns = 12

    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(block.text)

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tu in tool_uses:
                label = tu.input.get("query") or tu.input.get("url") or tu.name
                print(f"  [{tu.name}] {label[:80]}")
                result = execute_tool(tu.name, tu.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": tu.id, "content": result}
                )

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("  Basketball Ranking Bot  🏀")
    print("  Powered by Claude claude-opus-4-6")
    print("=" * 60)

    if len(sys.argv) > 1:
        run_bot(" ".join(sys.argv[1:]))
        return

    while True:
        print("\nWhat do you want ranked? (or 'quit' to exit)")
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        run_bot(query)


if __name__ == "__main__":
    main()
