"""Log in to Garmin Connect once and persist tokens (default: ~/.garminconnect)."""

import os
import sys
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

TOKEN_DIR = os.path.expanduser(os.environ.get("GARMIN_TOKEN_DIR", "~/.garminconnect"))


def main() -> None:
    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "")
    if not email or not password:
        print(
            "Set GARMIN_EMAIL and GARMIN_PASSWORD, then run again.",
            file=sys.stderr,
        )
        sys.exit(1)

    token_path = str(Path(TOKEN_DIR).expanduser().resolve())
    client = Garmin(email, password)

    try:
        mfa_pending, _ = client.login(token_path)
    except GarminConnectTooManyRequestsError as e:
        print(
            "Garmin rate-limited this IP (429); no login strategy succeeded.\n"
            "Wait 15–60 minutes, switch networks (e.g. phone hotspot), and avoid "
            "running the login script in a tight loop.",
            file=sys.stderr,
        )
        print(f"Detail: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectAuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        sys.exit(1)
    except GarminConnectConnectionError as e:
        print(f"Network or Garmin service error: {e}", file=sys.stderr)
        sys.exit(1)

    if mfa_pending:
        print(
            "MFA is required. Complete verification in an interactive terminal per "
            "the library prompts, or use an MFA-capable flow.",
            file=sys.stderr,
        )
        sys.exit(2)

    print("Login succeeded; tokens saved.")
    print(f"  Directory: {token_path}")
    print(f"  Display name: {getattr(client, 'display_name', '') or '(none)'}")
    print(
        "\nNote: Log lines like \"mobile … 429\" mean the mobile login path was "
        "rate-limited; the client may still succeed via web/portal flows. If this "
        "script prints success, the session is usually usable."
    )


if __name__ == "__main__":
    main()
