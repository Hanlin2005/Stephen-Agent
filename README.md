# AI Price Comparison Agent

Searches Amazon, eBay, Temu, Walmart, Best Buy, and more to find the cheapest price for any product.

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Set your Anthropic API key**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running

**Interactive mode** — prompts you to enter products one at a time:

```bash
python agent.py
```

**Single query mode** — pass the product directly as an argument:

```bash
python agent.py "Sony WH-1000XM5 headphones"
python agent.py "iPhone 15 128GB case"
python agent.py "standing desk"
```

## Example output

```
Searching for: Sony WH-1000XM5
============================================================
  [tool: search_web] sony wh-1000xm5 price site:amazon.com
  [tool: search_web] sony wh-1000xm5 cheapest price ebay walmart temu
  [tool: fetch_page] https://www.amazon.com/...

| Store    | Product                        | Price   | URL                  |
|----------|--------------------------------|---------|----------------------|
| Temu     | Sony WH-1000XM5 (3rd party)    | $189.99 | https://temu.com/... |
| Walmart  | Sony WH-1000XM5                | $279.99 | https://walmart...   |
| Amazon   | Sony WH-1000XM5                | $299.99 | https://amazon...    |
| eBay     | Sony WH-1000XM5 (used)         | $319.00 | https://ebay.com/... |
| Best Buy | Sony WH-1000XM5                | $349.99 | https://bestbuy...   |

Best deal: Temu at $189.99
============================================================
```
