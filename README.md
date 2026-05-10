# Garmin Connect MCP

Expose Garmin Connect health and training data to Claude Desktop and other MCP clients via the [Model Context Protocol](https://modelcontextprotocol.io/). The server implementation lives in `garmin_mcp_server.py`. See `garmin-mcp-setup-guide.md` for alternative setups (e.g. garmy + local DB).

## Requirements

- Python 3.10+ (3.11+ recommended)
- A Garmin Connect account
- Claude Desktop or another MCP-capable client

## Install

```bash
pip install -r requirements.txt
```

## First-time login (save tokens)

In PowerShell:

```powershell
$env:GARMIN_EMAIL="your-email@example.com"
$env:GARMIN_PASSWORD="your-secure-password"
python login_once.py
```

Tokens are stored under `~/.garminconnect` by default (override with `GARMIN_TOKEN_DIR`). If you see HTTP 429 on mobile login endpoints, the library may still succeed via other strategies; follow the script output.

## Claude Desktop

Edit your Claude Desktop config (path varies by install; often `%APPDATA%\Claude\claude_desktop_config.json`). Add an entry under `mcpServers`, for example:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "python",
      "args": [
        "C:\\path\\to\\Garmin Connect Claude\\garmin_mcp_server.py"
      ],
      "env": {
        "GARMIN_EMAIL": "your-email@example.com",
        "GARMIN_PASSWORD": "your-secure-password"
      }
    }
  }
}
```

- Set `args` to the **absolute path** of `garmin_mcp_server.py` on your machine (escape backslashes as `\\` in JSON).
- If `python` is not on `PATH`, set `command` to your Python executable path.
- Replace credentials with your own; **do not** commit real secrets to git.

Quit Claude Desktop fully and restart. You can then call `garmin_*` tools (e.g. `garmin_daily_summary`, `garmin_devices`).

## Security

- Prefer environment variables or a local-only config; never push `claude_desktop_config.json` with real passwords to a public repo.
- If credentials leaked, rotate your Garmin password and review account activity.

## Repository layout

| File | Purpose |
|------|---------|
| `garmin_mcp_server.py` | MCP server entrypoint |
| `login_once.py` | One-shot login and token save |
| `requirements.txt` | Python dependencies |
| `garmin-mcp-setup-guide.md` | Setup options (garmy vs custom server) |

## License

Follow any license file in the repository; if none is present, treat as personal / educational use only.
