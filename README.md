# Basketball Ranking Bot 🏀

Ask anything about basketball rankings and get a live, data-driven answer — teams, players, stats, positions, historical seasons, and more.

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

**Interactive mode** — type questions one at a time:

```bash
python bot.py
```

**Single query mode** — pass the question as an argument:

```bash
python bot.py "rank the top 10 NBA teams right now"
python bot.py "best point guards this season by assists"
python bot.py "top scorers in the NBA 2024-25"
python bot.py "rank all 30 NBA teams by defensive rating"
python bot.py "best rookies this season"
```

## Example output

```
Query: rank the top 5 NBA teams right now
============================================================
  [search_web] NBA standings 2024-25 season current
  [fetch_page] https://www.espn.com/nba/standings

**NBA Team Rankings — 2024-25 Season (as of Feb 2025)**

1. Cleveland Cavaliers (40-12, .769 Win%)
2. Oklahoma City Thunder (39-12, .765 Win%)
3. Boston Celtics (37-15, .711 Win%)
4. Houston Rockets (35-17, .673 Win%)
5. Memphis Grizzlies (34-18, .654 Win%)

The Cavaliers are the surprise story of the season, posting the best
record in the league — a major leap from recent years. OKC continues
its ascent behind Shai Gilgeous-Alexander, while Boston looks to defend
its championship.
============================================================
```
