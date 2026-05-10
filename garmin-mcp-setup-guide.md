# Garmin × Claude MCP server setup

## Overview

This guide helps you run an MCP (Model Context Protocol) server so Claude can read your Garmin health and training data. After setup you can ask things like:

- “How has my sleep quality trended over the last month?”
- “Was my training load too high last week?”
- “How has my resting heart rate changed recently?”
- “Given my HRV and Body Battery, is a hard workout reasonable today?”

---

## Choose an approach

| | Option A: garmy (recommended) | Option B: custom server (this repo) |
|---|---|---|
| Difficulty | Easier | More involved |
| Notes | Bundled MCP + local SQLite | Full control, live Garmin API |
| Best for | Quick start, historical analysis | Custom tools / live data |

---

## Option A: garmy (~10 minutes)

### Prerequisites

- Python 3.8+
- Garmin Connect account (same as the app / website)
- Claude Desktop (macOS / Windows)

### 1. Install garmy

```bash
pip install "garmy[all]"
```

### 2. Sign in to Garmin Connect

First run logs in; later runs refresh tokens:

```python
# login.py — run once
from garmy import AuthClient

auth = AuthClient()
auth.login("your-garmin-email", "your-garmin-password")
print("Login OK — token saved.")
```

```bash
python login.py
```

> If MFA is enabled, enter the code when prompted.

### 3. Sync into the local database

```bash
garmy-sync sync --last-days 30
garmy-sync status
```

Health data is stored in SQLite; the MCP server reads locally (fast and stable).

### 4. Configure Claude Desktop

Edit the Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Example:

```json
{
  "mcpServers": {
    "garmy-localdb": {
      "command": "garmy-mcp",
      "args": ["server", "--database", "/path/to/health.db", "--max-rows", "500"]
    }
  }
}
```

> Run `garmy-mcp config` for suggested settings.  
> `garmy-mcp info --database health.db` shows DB path and contents.

### 5. Restart Claude Desktop

### Scheduled sync

**macOS / Linux (cron, daily 07:00):**

```bash
crontab -e
# add:
0 7 * * * /usr/local/bin/garmy-sync sync --last-days 7
```

**Windows (Task Scheduler / PowerShell example):**

```powershell
schtasks /create /tn "GarmySync" /tr "garmy-sync sync --last-days 7" /sc daily /st 07:00
```

---

## Option B: Custom server (`python-garminconnect` + FastMCP)

Use this when you want live API access or custom tools. **This repository** already ships the server:

- `garmin_mcp_server.py` — MCP tools
- `login_once.py` — save tokens locally
- `requirements.txt` — dependencies

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Log in once

See [README.md](README.md) (`login_once.py` + `GARMIN_EMAIL` / `GARMIN_PASSWORD`).

### 3. Configure Claude Desktop

```json
{
  "mcpServers": {
    "garmin": {
      "command": "python",
      "args": ["/absolute/path/to/garmin_mcp_server.py"],
      "env": {
        "GARMIN_EMAIL": "your-email@example.com",
        "GARMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

Use your real absolute path and credentials; do not commit secrets.

### 4. Restart Claude Desktop

---

## Example prompts

### Daily health

- “Summarize my health stats for today.”
- “How was last night’s sleep — enough deep sleep?”
- “What did my stress look like over the past week?”
- “What’s my Body Battery now?”

### Training

- “List my last 10 runs.”
- “Relate pace and heart rate on my last run.”
- “How has aerobic training effect looked lately?”
- “From VO2 Max, estimate my half-marathon time.”

### Coaching-style

- “From HRV and sleep, what training fits today?”
- “Summarize this week’s training and recovery.”
- “Is resting HR trending down — what might that mean?”
- “Compare my last five runs; which was best and why?”

---

## FAQ

### Token expired?

`garminconnect` refreshes tokens when possible. On auth errors, run `login_once.py` again.

### MFA?

Enter the code in the terminal on first login. After tokens are saved you usually do not need MFA each time.

### Claude web (claude.ai)?

MCP is primarily supported in Claude Desktop; web support is evolving. Alternatives: export CSV periodically, or host a remote MCP (needs a reachable URL).

### Is data safe?

Data stays local; the MCP process runs on your machine. Prefer env vars for passwords, not hard-coded secrets in repos.

### Will Garmin ban my account?

These clients use the same style of authentication as the official app. Avoid hammering the API: no tight loops, no huge concurrency. Option A (local DB) reduces API calls.
